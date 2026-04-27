# Model weights

This directory must contain the bundled model weights at deploy time. They are
intentionally not committed to git — fetch them once on a build machine that
has internet access, place them here, then ship them as part of the offline
USB bundle (see `scripts/bundle.sh`).

Required files:

- `yolo11n.pt` — YOLO11 nano person detector (Ultralytics).
- `osnet_x0_25.pth` — OSNet-x0.25 ReID weights (TorchReID model zoo).

Acquire (run on a connected machine):

```bash
# YOLO11
yolo download model=yolo11n.pt
mv yolo11n.pt workers/models/

# OSNet
python -c "from torchreid.utils import FeatureExtractor; \
  FeatureExtractor(model_name='osnet_x0_25', model_path=None, device='cpu')"
# the OSNet weights land under ~/.cache/torch/checkpoints/ — copy that file here as osnet_x0_25.pth
```
