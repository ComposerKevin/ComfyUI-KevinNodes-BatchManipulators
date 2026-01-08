import torch
import torch.nn.functional as F
from comfy.utils import common_upscale

def resize_latent_tensor(tensor, target_h, target_w):
    # tensor is [B, C, H, W]
    if tensor.shape[2] != target_h or tensor.shape[3] != target_w:
        return common_upscale(tensor, target_w, target_h, "bilinear", "center")
    return tensor

def resize_mask_tensor(tensor, target_h, target_w):
    # mask is [B, H, W] (usually) or [1, H, W]
    # Latent masks in Comfy are often [B, 1, H, W] or [B, H, W] depending on where they came from.
    # We normalize to [B, 1, H, W] for interpolation then squeeze back if needed.
    
    dims = tensor.dim()
    if dims == 3:
        tensor = tensor.unsqueeze(1)
    
    if tensor.shape[2] != target_h or tensor.shape[3] != target_w:
        tensor = F.interpolate(tensor, size=(target_h, target_w), mode="nearest")
        
    if dims == 3:
        tensor = tensor.squeeze(1)
        
    return tensor

def normalize_latent_masks(latents_a, latents_b):
    """
    Ensures both latent dictionaries have 'noise_mask' if at least one of them has it.
    Returns the two mask tensors (or None).
    """
    mask_a = latents_a.get("noise_mask")
    mask_b = latents_b.get("noise_mask")
    
    if mask_a is None and mask_b is None:
        return None, None
    
    # Get batch sizes and dimensions
    s_a = latents_a["samples"]
    s_b = latents_b["samples"]
    
    # If A missing mask, create ones (default behavior in Comfy is usually ones for full noise, 
    # but for inpainting, missing mask usually implies full area is valid/masked? 
    # Actually Comfy LatentBatch uses ones if missing).
    if mask_a is None:
        mask_a = torch.ones((s_a.shape[0], 1, s_a.shape[2], s_a.shape[3]), device=s_a.device, dtype=s_a.dtype)
    
    if mask_b is None:
        mask_b = torch.ones((s_b.shape[0], 1, s_b.shape[2], s_b.shape[3]), device=s_b.device, dtype=s_b.dtype)

    # Ensure 4 dimensions [B, 1, H, W] for consistency during manipulation
    if mask_a.dim() == 3: mask_a = mask_a.unsqueeze(1)
    if mask_b.dim() == 3: mask_b = mask_b.unsqueeze(1)
        
    return mask_a, mask_b

class KevinNodeInsertLatentsToBatchIndexed:
    
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "insert"
    CATEGORY = "kevin_nodes/latents"
    DESCRIPTION = """
Inserts latents into a batch at specified indices.
Handles resizing of inserted latents to match the original batch.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "original_latents": ("LATENT",),
                "latents_to_insert": ("LATENT",),
                "indexes": ("STRING", {"default": "0", "multiline": False}),
            },
            "optional": {
                "mode": (["replace", "insert"],),
            }
        }
    
    def insert(self, original_latents, latents_to_insert, indexes, mode="replace"):
        if indexes.strip() == "":
            return (original_latents,)

        # Clone to avoid modifying input in place
        out_latents = {k: v.clone() for k, v in original_latents.items()}
        
        samples_orig = out_latents["samples"]
        samples_insert = latents_to_insert["samples"]
        
        # Handle Masks
        mask_orig, mask_insert = normalize_latent_masks(original_latents, latents_to_insert)
        has_masks = mask_orig is not None
        
        target_h, target_w = samples_orig.shape[2], samples_orig.shape[3]
        
        try:
            index_list = [int(idx.strip()) for idx in indexes.split(',')]
        except ValueError:
            print("KevinNodeInsertLatentsToBatchIndexed: Invalid index format")
            return (original_latents,)
            
        indices_tensor = torch.tensor(index_list, dtype=torch.long)
        
        # Prepare insertion list
        # If samples_insert is single frame [1, C, H, W], we cycle it.
        # If it's a batch, we cycle through the batch.
        
        if mode == "replace":
            for i, index in enumerate(indices_tensor):
                if index < len(samples_orig):
                    # Get sample to insert
                    s = samples_insert[i % len(samples_insert)].unsqueeze(0)
                    s = resize_latent_tensor(s, target_h, target_w)
                    samples_orig[index] = s.squeeze(0)
                    
                    if has_masks:
                        m = mask_insert[i % len(mask_insert)].unsqueeze(0)
                        m = resize_mask_tensor(m, target_h, target_w)
                        mask_orig[index] = m.squeeze(0)
                        
        else: # Insert mode
            new_samples = []
            new_masks = []
            
            # Logic similar to mask insertion
            sorted_indices, _ = torch.sort(indices_tensor)
            
            insertion_map = {}
            for i, idx in enumerate(index_list):
                s = samples_insert[i % len(samples_insert)].unsqueeze(0)
                s = resize_latent_tensor(s, target_h, target_w)
                
                m = None
                if has_masks:
                    m = mask_insert[i % len(mask_insert)].unsqueeze(0)
                    m = resize_mask_tensor(m, target_h, target_w)
                
                if idx not in insertion_map:
                    insertion_map[idx] = []
                insertion_map[idx].append((s, m))
            
            orig_ptr = 0
            max_index = max(index_list) if index_list else 0
            loop_limit = max(len(samples_orig) + len(index_list), max_index + 1)
            
            for i in range(loop_limit):
                if i in insertion_map and len(insertion_map[i]) > 0:
                    s, m = insertion_map[i].pop(0)
                    new_samples.append(s)
                    if has_masks: new_masks.append(m)
                else:
                    if orig_ptr < len(samples_orig):
                        new_samples.append(samples_orig[orig_ptr].unsqueeze(0))
                        if has_masks: new_masks.append(mask_orig[orig_ptr].unsqueeze(0))
                        orig_ptr += 1
            
            # Append remaining original
            while orig_ptr < len(samples_orig):
                new_samples.append(samples_orig[orig_ptr].unsqueeze(0))
                if has_masks: new_masks.append(mask_orig[orig_ptr].unsqueeze(0))
                orig_ptr += 1
                
            # Append remaining insertions (if index > len)
            for idx in sorted(insertion_map.keys()):
                while len(insertion_map[idx]) > 0:
                    s, m = insertion_map[idx].pop(0)
                    new_samples.append(s)
                    if has_masks: new_masks.append(m)

            if new_samples:
                samples_orig = torch.cat(new_samples, dim=0)
                if has_masks:
                    mask_orig = torch.cat(new_masks, dim=0)

        out_latents["samples"] = samples_orig
        if has_masks:
            out_latents["noise_mask"] = mask_orig
        elif "noise_mask" in out_latents:
            del out_latents["noise_mask"]
            
        return (out_latents,)

class KevinNodeRemoveLatentsFromBatchIndexed:
    
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "remove"
    CATEGORY = "kevin_nodes/latents"
    DESCRIPTION = """
Removes latents at specified indices.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latents": ("LATENT",),
                "indexes": ("STRING", {"default": "0", "multiline": False}),
            }
        }
    
    def remove(self, latents, indexes):
        if indexes.strip() == "":
            return (latents,)
            
        out_latents = {k: v.clone() for k, v in latents.items()}
        samples = out_latents["samples"]
        mask = out_latents.get("noise_mask")
        
        try:
            total = samples.shape[0]
            indices_to_remove = set()
            for idx in indexes.split(','):
                val = int(idx.strip())
                if val < 0: val = total + val
                indices_to_remove.add(val)
        except ValueError:
            return (latents,)
            
        kept_samples = []
        kept_masks = []
        
        for i in range(total):
            if i not in indices_to_remove:
                kept_samples.append(samples[i])
                if mask is not None:
                    # Handle mask shape variations [B, 1, H, W] or [B, H, W]
                    if i < mask.shape[0]:
                        kept_masks.append(mask[i])
                    else:
                        # If mask batch is smaller than samples (broadcast), keep repeating last?
                        # Standard comfy behavior is usually 1:1 or 1:N. 
                        kept_masks.append(mask[min(i, mask.shape[0]-1)])

        if not kept_samples:
            # Return empty-ish latent to prevent crash, or just 1 frame zeroed
            # Returning 1 frame zeroed is safer
            kept_samples.append(torch.zeros_like(samples[0]))
            if mask is not None:
                kept_masks.append(torch.zeros_like(mask[0]))

        out_latents["samples"] = torch.stack(kept_samples, dim=0)
        if mask is not None:
            out_latents["noise_mask"] = torch.stack(kept_masks, dim=0)
            
        return (out_latents,)

class KevinNodeZipLatentBatches:
    
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "zip_latents"
    CATEGORY = "kevin_nodes/latents"
    DESCRIPTION = """
Interleaves two latent batches. Resizes Batch B to match Batch A.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latents_a": ("LATENT",),
                "latents_b": ("LATENT",),
            }
        }
    
    def zip_latents(self, latents_a, latents_b):
        out_latents = {}
        
        s_a = latents_a["samples"]
        s_b = latents_b["samples"]
        
        target_h, target_w = s_a.shape[2], s_a.shape[3]
        
        # Normalize masks
        m_a, m_b = normalize_latent_masks(latents_a, latents_b)
        has_masks = m_a is not None
        
        len_a = s_a.shape[0]
        len_b = s_b.shape[0]
        target_len = max(len_a, len_b)
        
        zipped_samples = []
        zipped_masks = []
        
        for i in range(target_len):
            # A
            idx_a = i % len_a
            sample_a = s_a[idx_a].unsqueeze(0)
            zipped_samples.append(sample_a)
            if has_masks:
                zipped_masks.append(m_a[idx_a].unsqueeze(0))
            
            # B
            idx_b = i % len_b
            sample_b = s_b[idx_b].unsqueeze(0)
            sample_b = resize_latent_tensor(sample_b, target_h, target_w)
            zipped_samples.append(sample_b)
            if has_masks:
                mask_b_resized = resize_mask_tensor(m_b[idx_b].unsqueeze(0), target_h, target_w)
                zipped_masks.append(mask_b_resized)
                
        out_latents["samples"] = torch.cat(zipped_samples, dim=0)
        if has_masks:
            out_latents["noise_mask"] = torch.cat(zipped_masks, dim=0)
            
        # Copy batch_index if present in A (ignoring B's batch index for simplicity)
        if "batch_index" in latents_a:
            # This is complex to zip correctly if they differ, skipping for now to avoid errors
            pass
            
        return (out_latents,)

class KevinNodeRepeatLatentIndices:
    
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "repeat"
    CATEGORY = "kevin_nodes/latents"
    DESCRIPTION = """
Repeats specific latents within a batch N times.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latents": ("LATENT",),
                "indexes": ("STRING", {"default": "0", "multiline": False}),
                "repeats": ("INT", {"default": 2, "min": 1, "max": 100}),
            }
        }
    
    def repeat(self, latents, indexes, repeats):
        out_latents = {k: v.clone() for k, v in latents.items()}
        samples = out_latents["samples"]
        mask = out_latents.get("noise_mask")
        
        try:
            target_indices = set([int(idx.strip()) for idx in indexes.split(',')])
        except ValueError:
            return (latents,)
            
        new_samples = []
        new_masks = []
        
        for i in range(samples.shape[0]):
            s = samples[i]
            m = mask[i] if mask is not None else None
            
            count = repeats if i in target_indices else 1
            
            for _ in range(count):
                new_samples.append(s)
                if m is not None:
                    new_masks.append(m)
                    
        out_latents["samples"] = torch.stack(new_samples, dim=0)
        if mask is not None:
            out_latents["noise_mask"] = torch.stack(new_masks, dim=0)
            
        return (out_latents,)

NODE_CLASS_MAPPINGS = {
    "KevinNodeInsertLatentsToBatchIndexed": KevinNodeInsertLatentsToBatchIndexed,
    "KevinNodeRemoveLatentsFromBatchIndexed": KevinNodeRemoveLatentsFromBatchIndexed,
    "KevinNodeZipLatentBatches": KevinNodeZipLatentBatches,
    "KevinNodeRepeatLatentIndices": KevinNodeRepeatLatentIndices
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KevinNodeInsertLatentsToBatchIndexed": "Insert Latents To Batch Indexed (Kevin)",
    "KevinNodeRemoveLatentsFromBatchIndexed": "Remove Latents From Batch Indexed (Kevin)",
    "KevinNodeZipLatentBatches": "Zip Latent Batches (Kevin)",
    "KevinNodeRepeatLatentIndices": "Repeat Latent Indices (Kevin)"
}
