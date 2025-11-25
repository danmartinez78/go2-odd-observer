# BEV Auto-Crop Enhancement - Feature Complete

**Status**: ✅ Ready to merge to dev  
**Date**: November 25, 2025

## What's Included

### 1. BEV Auto-Crop Function
- 100% obstacle preservation
- 65-72% size reduction  
- Robot-centered crops
- 13 passing unit tests

### 2. Transformation Pipeline
- Rotation: 0°/90°/180°/270° (data-source specific)
- Horizontal flip option
- Auto-crop integration

### 3. Simplified Channels
- **Removed**: Density (redundant)
- **Kept**: Occupancy, Height, Roughness

### 4. Data Reorganization
- `data/production/` - Production data
- `data/test/` - Test samples
- `data/archive/` - Reference data

## Sim Data Ready ✅

**Production**: 62 windows in `data/production/sim_1_0/`  
**Test**: 6 windows in `data/test/sim/`  
**Transformations**: 90° rotation + horizontal flip + auto-crop

## Real Data Status ⚠️

**Blocked**: Accumulated voxel maps cause aliasing  
**Solution**: Need per-scan LiDAR topic  
**Ready**: Auto-crop works, awaiting better data source

## Migration Notes

**BEV channels**: 4 → 3 (removed density)  
**Data paths**: `data/processed/` → `data/production/`  
**Details**: See `docs/BEV_TRANSFORMATION_STATUS.md`

---

Ready to merge and start agent rework with clean test data!
