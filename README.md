# ComfyUI KevinNodes BatchManipulators

A collection of custom nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) focused on advanced **Batch manipulation** for both **Masks** and **Latents**.

While many custom node packs offer image batch manipulation, precise control over **Mask Batches** and **Latent Batches** is often missing. These nodes allow you to treat batches like arrays: inserting at specific indices, removing specific frames, zipping two batches together, and repeating specific frames.

## 📥 Installation

### Method 1: ComfyUI Manager (Recommended)
1. Install [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager).
2. Click **"Install via Git URL"**.
3. Paste the repository URL: `https://github.com/ComposerKevin/ComfyUI-KevinNodes-BatchManipulators`

### Method 2: Manual Installation
1. Navigate to your ComfyUI `custom_nodes` directory.
2. Open a terminal/command prompt.
3. Run the following command:
   ```bash
   git clone https://github.com/ComposerKevin/ComfyUI-KevinNodes-BatchManipulators
   ```
4. Restart ComfyUI.

---

## 🧩 The Nodes

### 🎭 Mask Nodes
Located under: `kevin_nodes` > `masking`

#### 1. Insert Masks To Batch Indexed
Allows you to inject a mask (or a batch of masks) into an existing batch at specific index positions.
*   **Inputs:** `original_masks`, `masks_to_insert`, `indexes`, `mode` (replace/insert).
*   **Features:** Automatically resizes the inserted masks to match the dimensions of the original batch.

#### 2. Remove Masks From Batch Indexed
Removes specific masks from a batch based on their index.
*   **Inputs:** `masks`, `indexes`.
*   **Features:** Supports negative indexing (e.g., `-1` removes the last frame).

#### 3. Zip Mask Batches
Interleaves two mask batches (A and B) into a single sequence (A1, B1, A2, B2, ...).
*   **Inputs:** `masks_a`, `masks_b`, `match_dimensions`.
*   **Use Case:** Great for creating flickering mask effects or merging two different animation sequences frame-by-frame.

#### 4. Repeat Mask Indices
Repeats specific frames within a batch `N` times.
*   **Inputs:** `masks`, `indexes`, `repeats`.
*   **Use Case:** Useful for "freezing" a mask for a specific duration within an animation sequence.

---

### 🎨 Latent Nodes
Located under: `kevin_nodes` > `latents`

**Note:** All Latent nodes automatically handle and resize the `noise_mask` (inpainting mask) attached to the latents if present.

#### 1. Insert Latents To Batch Indexed
Inserts latents into a batch at specified indices.
*   **Inputs:** `original_latents`, `latents_to_insert`, `indexes`, `mode` (replace/insert).
*   **Features:** 
    *   Resizes inserted latents to match the resolution of the original batch.
    *   Handles `noise_mask` alignment automatically.

#### 2. Remove Latents From Batch Indexed
Removes specific latents from a batch based on their index.
*   **Inputs:** `latents`, `indexes`.

#### 3. Zip Latent Batches
Interleaves two latent batches (A and B) into a single sequence.
*   **Inputs:** `latents_a`, `latents_b`.
*   **Features:** Resizes Batch B to match the resolution of Batch A.

#### 4. Repeat Latent Indices
Repeats specific latents within a batch `N` times.
*   **Inputs:** `latents`, `indexes`, `repeats`.

----

## Contributors
- ComposerKevin: Main developer. 

## AI-Generated Content Disclosure Notice
Coding process of this software has AI code generator involved. 

## 📄 License
LGPL 2.0
