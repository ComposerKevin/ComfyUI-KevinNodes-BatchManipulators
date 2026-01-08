# ComfyUI KevinNodes BatchManipulators
# Author: Github @ComposerKevin
# License: LGPL 2.0

import torch
import torch.nn.functional as F

# Helper function to ensure masks match dimensions before stacking/catting
def resize_mask_if_needed(mask_tensor, target_h, target_w):
    # mask_tensor expected to be [H, W] or [B, H, W]
    if mask_tensor.dim() == 2:
        h, w = mask_tensor.shape
    else:
        h, w = mask_tensor.shape[-2:]

    if (h, w) != (target_h, target_w):
        # Add dimensions for interpolation (B, C, H, W) -> (1, 1, H, W)
        if mask_tensor.dim() == 2:
            temp = mask_tensor.unsqueeze(0).unsqueeze(0)
            temp = F.interpolate(temp, size=(target_h, target_w), mode="nearest")
            return temp.squeeze(0).squeeze(0)
        else:
            temp = mask_tensor.unsqueeze(1) # Add channel dim
            temp = F.interpolate(temp, size=(target_h, target_w), mode="nearest")
            return temp.squeeze(1)
    return mask_tensor

class KevinNodeInsertMasksToBatchIndexed:
    
    RETURN_TYPES = ("MASK",)
    FUNCTION = "insertmasksfrombatch"
    CATEGORY = "kevin_nodes/masking"
    DESCRIPTION = """
Inserts masks at the specified indices into the original mask batch.
If 'replace' mode is on, it overwrites the mask at that index.
If 'insert' mode is on, it injects the mask, shifting subsequent masks to the right.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "original_masks": ("MASK",),
                "masks_to_insert": ("MASK",),
                "indexes": ("STRING", {"default": "0, 1, 2", "multiline": False}),
            },
            "optional": {
                "mode": (["replace", "insert"],),
            }
        }
    
    def insertmasksfrombatch(self, original_masks, masks_to_insert, indexes, mode="replace"):
        if indexes.strip() == "":
            return (original_masks,)

        input_masks = original_masks.clone()
        
        try:
            index_list = [int(index.strip()) for index in indexes.split(',')]
        except ValueError:
            print("KevinNodeInsertMasksToBatchIndexed: Error parsing indexes, returning original masks")
            return (original_masks,)
            
        indices_tensor = torch.tensor(index_list, dtype=torch.long)
        
        if not isinstance(masks_to_insert, torch.Tensor):
            masks_to_insert = torch.tensor(masks_to_insert)

        # Handle single mask input (H,W) vs batch (B,H,W)
        if masks_to_insert.dim() == 2:
            masks_to_insert = masks_to_insert.unsqueeze(0)
        
        target_h, target_w = input_masks.shape[-2], input_masks.shape[-1]

        if mode == "replace":
            for i, index in enumerate(indices_tensor):
                if index < len(input_masks):
                    mask_to_use = masks_to_insert[i % len(masks_to_insert)]
                    input_masks[index] = resize_mask_if_needed(mask_to_use, target_h, target_w)
        else:
            new_masks = []
            insert_offset = 0
            original_idx = 0
            
            # Sort indices for sequential insertion logic
            sorted_indices, _ = torch.sort(indices_tensor)
            
            # We iterate enough times to cover original items + inserted items
            total_length = len(input_masks) + len(sorted_indices)
            
            # Map sorted indices back to the order in masks_to_insert
            # This is a bit complex: we want to insert masks_to_insert[0] at index_list[0]
            # regardless of whether index_list[0] is smaller or larger than index_list[1].
            # However, standard list construction is sequential. 
            # Simplified approach: We construct the list sequentially.
            
            # Create a map of target_index -> mask_to_insert
            insertion_map = {}
            for i, idx in enumerate(index_list):
                mask = masks_to_insert[i % len(masks_to_insert)]
                # If multiple insertions at same index, we create a list
                if idx not in insertion_map:
                    insertion_map[idx] = []
                insertion_map[idx].append(mask)

            current_output_idx = 0
            
            # We iterate through original masks and insert before them if needed
            # But since indices refer to the *final* list, we build up to it.
            
            # Easier logic: Construct a list with placeholders, then fill
            # But we don't know final size if indices are out of bounds.
            # Let's stick to the "Insert at X" logic relative to the growing list? 
            # No, usually "Insert at Index 5" means the result has that item at index 5.
            
            # Robust List Construction
            result_list = []
            
            # We need to place original items and new items.
            # We can treat this as a merge.
            
            # 1. Identify which indices in the FINAL list are reserved for insertions
            reserved_indices = set(index_list)
            
            orig_ptr = 0
            
            # We go up to a theoretical max length. 
            # If an index is way out of bounds (e.g. index 100 on a list of 5), we append at end.
            
            max_index = max(index_list) if index_list else 0
            estimated_len = len(input_masks) + len(index_list)
            loop_limit = max(estimated_len, max_index + 1)

            for i in range(loop_limit):
                # Check if this index is a target for insertion
                if i in insertion_map and len(insertion_map[i]) > 0:
                    # Pop the mask intended for this index
                    # (Handles multiple insertions at same index by taking first available)
                    m = insertion_map[i].pop(0)
                    new_masks.append(resize_mask_if_needed(m, target_h, target_w))
                else:
                    # Otherwise take from original
                    if orig_ptr < len(input_masks):
                        new_masks.append(input_masks[orig_ptr])
                        orig_ptr += 1
            
            # If we still have original masks left (because we didn't reach their slots yet)
            while orig_ptr < len(input_masks):
                new_masks.append(input_masks[orig_ptr])
                orig_ptr += 1
                
            # If we have insertions beyond the length of original (append to end)
            # The loop above handles up to max_index, but let's ensure we didn't miss any
            # due to logic gaps.
            for idx in sorted(insertion_map.keys()):
                while len(insertion_map[idx]) > 0:
                    m = insertion_map[idx].pop(0)
                    new_masks.append(resize_mask_if_needed(m, target_h, target_w))

            if new_masks:
                input_masks = torch.stack(new_masks, dim=0)
        
        return (input_masks,)


class KevinNodeRemoveMasksFromBatchIndexed:
    
    RETURN_TYPES = ("MASK",)
    FUNCTION = "remove_masks"
    CATEGORY = "kevin_nodes/masking"
    DESCRIPTION = """
Removes masks at the specified indices from the batch.
Indices are 0-based.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "masks": ("MASK",),
                "indexes": ("STRING", {"default": "0", "multiline": False}),
            }
        }
    
    def remove_masks(self, masks, indexes):
        if indexes.strip() == "":
            return (masks,)
            
        try:
            # Parse and handle negative indices
            total_masks = masks.shape[0]
            indices_to_remove = set()
            for idx in indexes.split(','):
                val = int(idx.strip())
                if val < 0:
                    val = total_masks + val
                indices_to_remove.add(val)
        except ValueError:
            print("KevinNodeRemoveMasksFromBatchIndexed: Invalid index format")
            return (masks,)

        kept_masks = []
        for i in range(total_masks):
            if i not in indices_to_remove:
                kept_masks.append(masks[i])
        
        if len(kept_masks) == 0:
            # Return a single empty mask to prevent downstream errors
            # keeping dimensions of original
            return (torch.zeros((1, masks.shape[1], masks.shape[2]), device=masks.device, dtype=masks.dtype),)
            
        return (torch.stack(kept_masks, dim=0),)


class KevinNodeZipMaskBatches:
    
    RETURN_TYPES = ("MASK",)
    FUNCTION = "zip_batches"
    CATEGORY = "kevin_nodes/masking"
    DESCRIPTION = """
Interleaves two mask batches (A, B) into a single batch (A1, B1, A2, B2...).
Useful for creating alternating patterns or comparing sequences.
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "masks_a": ("MASK",),
                "masks_b": ("MASK",),
                "match_dimensions": ("BOOLEAN", {"default": True}),
            }
        }
    
    def zip_batches(self, masks_a, masks_b, match_dimensions):
        # Ensure 3D (B, H, W)
        if masks_a.dim() == 2: masks_a = masks_a.unsqueeze(0)
        if masks_b.dim() == 2: masks_b = masks_b.unsqueeze(0)
        
        len_a = masks_a.shape[0]
        len_b = masks_b.shape[0]
        target_len = max(len_a, len_b)
        
        target_h, target_w = masks_a.shape[1], masks_a.shape[2]
        
        zipped = []
        
        for i in range(target_len):
            # Get mask A (cycle if B is longer)
            if i < len_a:
                ma = masks_a[i]
            else:
                ma = masks_a[i % len_a]
                
            # Get mask B (cycle if A is longer)
            if i < len_b:
                mb = masks_b[i]
            else:
                mb = masks_b[i % len_b]
            
            if match_dimensions:
                mb = resize_mask_if_needed(mb, target_h, target_w)
                ma = resize_mask_if_needed(ma, target_h, target_w) # Just in case A varies internally, though unlikely in tensor
            
            zipped.append(ma)
            zipped.append(mb)
            
        return (torch.stack(zipped, dim=0),)


class KevinNodeRepeatMaskIndices:
    
    RETURN_TYPES = ("MASK",)
    FUNCTION = "repeat_indices"
    CATEGORY = "kevin_nodes/masking"
    DESCRIPTION = """
Repeats specific frames within a batch N times.
Example: Batch [A, B, C], Index "1", Repeats 3 -> Result [A, B, B, B, C].
"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "masks": ("MASK",),
                "indexes": ("STRING", {"default": "0", "multiline": False}),
                "repeats": ("INT", {"default": 2, "min": 1, "max": 100}),
            }
        }
    
    def repeat_indices(self, masks, indexes, repeats):
        if masks.dim() == 2: masks = masks.unsqueeze(0)
        
        try:
            target_indices = set([int(idx.strip()) for idx in indexes.split(',')])
        except ValueError:
            return (masks,)
            
        new_batch = []
        for i in range(masks.shape[0]):
            mask = masks[i]
            if i in target_indices:
                for _ in range(repeats):
                    new_batch.append(mask)
            else:
                new_batch.append(mask)
                
        return (torch.stack(new_batch, dim=0),)


NODE_CLASS_MAPPINGS = {
    "KevinNodeInsertMasksToBatchIndexed": KevinNodeInsertMasksToBatchIndexed,
    "KevinNodeRemoveMasksFromBatchIndexed": KevinNodeRemoveMasksFromBatchIndexed,
    "KevinNodeZipMaskBatches": KevinNodeZipMaskBatches,
    "KevinNodeRepeatMaskIndices": KevinNodeRepeatMaskIndices
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KevinNodeInsertMasksToBatchIndexed": "Insert Masks To Batch Indexed (Kevin)",
    "KevinNodeRemoveMasksFromBatchIndexed": "Remove Masks From Batch Indexed (Kevin)",
    "KevinNodeZipMaskBatches": "Zip Mask Batches (Kevin)",
    "KevinNodeRepeatMaskIndices": "Repeat Mask Indices (Kevin)"
}
