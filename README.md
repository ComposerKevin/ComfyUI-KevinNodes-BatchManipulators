# ComfyUI-KevinNodes-BatchManipulators

A collection of custom nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) focused on advanced **Batch manipulation**. 

While many custom node packs offer image batch manipulation, precise control over **Mask Batches** (arrays of masks) is often missing. These nodes allow you to treat mask batches like arrays: inserting at specific indices, removing specific frames, zipping two batches together, and repeating specific frames.

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

## 🧩 Nodes

All nodes can be found in the node menu under:  
`kevin_nodes` > `masking`

### 1. Insert Masks To Batch Indexed
Allows you to inject a mask (or a batch of masks) into an existing batch at specific index positions.

*   **Inputs:**
    *   `original_masks`: The main batch.
    *   `masks_to_insert`: The mask(s) you want to add.
    *   `indexes`: Comma-separated string (e.g., `0, 5, 10`).
    *   `mode`: 
        *   `replace`: Overwrites the mask at the target index.
        *   `insert`: Injects the mask at the target index, shifting subsequent masks to the right.
*   **Features:** Automatically resizes the inserted masks to match the dimensions of the original batch.

### 2. Remove Masks From Batch Indexed
Removes specific masks from a batch based on their index.

*   **Inputs:**
    *   `masks`: The input batch.
    *   `indexes`: Comma-separated string of indices to remove (e.g., `0, 2, 4`).
*   **Features:** Supports negative indexing (e.g., `-1` removes the last frame).

### 3. Zip Mask Batches
Interleaves two mask batches (A and B) into a single sequence (A1, B1, A2, B2, ...).

*   **Inputs:**
    *   `masks_a`: First batch.
    *   `masks_b`: Second batch.
    *   `match_dimensions`: If true, resizes Batch B to match Batch A's resolution.
*   **Use Case:** Great for creating flickering mask effects or merging two different animation sequences frame-by-frame.

### 4. Repeat Mask Indices
Repeats specific frames within a batch `N` times.

*   **Inputs:**
    *   `masks`: The input batch.
    *   `indexes`: The indices of the frames you want to repeat (e.g., `0` to repeat the first frame).
    *   `repeats`: How many times to repeat the selected frames.
*   **Use Case:** Useful for "freezing" a mask for a specific duration within an animation sequence.

---

## 🛠️ Compatibility

*   These nodes are designed to work with standard ComfyUI `MASK` types.
*   They handle dimension mismatches gracefully by resizing inputs to match the target batch using nearest-neighbor interpolation (to preserve hard edges common in masks).

## Contributors
- ComposerKevin: Main developer. 

## AI-Generated Content Note
Coding process of this software has AI code generator involved. 

## 📄 License
LGPL 2.0
