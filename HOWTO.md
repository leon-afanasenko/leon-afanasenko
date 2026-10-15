# Make your own

1. Fork or clone this repository. A profile repository must have the same name as your GitHub login.
2. Install Pillow (`pip install pillow`) and the portrait tool: `brew install TheZoraiz/ascii-image-converter/ascii-image-converter` (other systems: see its page).
3. Put your data into `profile.json`.
4. Pick a photo: face large in the frame, background clearly darker or lighter than the skin, light from the front.
5. Run `python3 make_profile.py photo.jpg --crop x0,y0,x1,y1` (the crop box is the face; try `--threshold 110` to `150`, `--width 50`).
6. Commit `README.md` and the two `profile-*.svg` files (dark and light). The photo stays on your machine.
