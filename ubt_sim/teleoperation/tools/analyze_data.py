#!/usr/bin/env python3
import h5py
import numpy as np
import os
import argparse
import cv2

def analyze_hdf5(file_path):
    print(f"\nAnalyzing file: {file_path}")
    try:
        with h5py.File(file_path, 'r') as f:
            # 1. 检查所有的数据集及其长度
            datasets = {}
            def get_datasets(name, obj):
                if isinstance(obj, h5py.Dataset):
                    datasets[name] = obj.shape[0]
            
            f.visititems(get_datasets)
            
            if not datasets:
                print("  [ERROR] No datasets found in file.")
                return

            print("  Datasets found:")
            lengths = []
            for name, length in datasets.items():
                print(f"    - {name}: {length} frames")
                lengths.append(length)
            
            # 2. 检查长度是否一致
            if len(set(lengths)) > 1:
                print(f"  [CRITICAL] Length mismatch detected! Lengths: {set(lengths)}")
            else:
                print(f"  [OK] All datasets have the same length ({lengths[0]} frames).")

            # 新增：检查时间戳抖动 (Jitter)
            ts_keys = [k for k in datasets if 'timestamp' in k]
            if ts_keys:
                ts_data = f[ts_keys[0]][:]
                intervals = np.diff(ts_data)
                avg_i = np.mean(intervals)
                std_i = np.std(intervals)
                print(f"  Timestamp Analysis ({ts_keys[0]}):")
                print(f"    - Avg: {avg_i:.4f}s ({1/avg_i:.2f}Hz), StdDev: {std_i:.4f}s")
                if std_i > (avg_i * 0.2): # 抖动超过均值的20%
                     print(f"    - [WARNING] High jitter detected!")
            else:
                print("  [INFO] No timestamp dataset found for Jitter analysis.")

            # 3. 检查数据更新情况 (检查是否有持续不变的信号)
            # 这有助于发现订阅是否挂掉或者频率太低
            for name in datasets:
                if 'color_images' in name:
                    continue # 图像跳过，下面单独检查
                
                data = f[name][:]
                if data.ndim >= 2:
                    # 检查是否有重复的帧
                    diffs = np.diff(data, axis=0)
                    zero_diffs = np.all(diffs == 0, axis=1)
                    duplicate_count = np.sum(zero_diffs)
                    max_consecutive = 0
                    current_consecutive = 0
                    for d in zero_diffs:
                        if d:
                            current_consecutive += 1
                            max_consecutive = max(max_consecutive, current_consecutive)
                        else:
                            current_consecutive = 0
                    
                    if duplicate_count > 0:
                        print(f"    - {name}: {duplicate_count} duplicate frames ({duplicate_count/len(data)*100:.2f}%). Max consecutive: {max_consecutive}")
                    else:
                        print(f"    - {name}: [OK] Clean signal (no duplicate frames).")

            # 4. 检查图像数据
            image_keys = [k for k in datasets if 'camera_head' in k]
            for img_key in image_keys:
                img_data = f[img_key]
                print(f"  Checking image dataset: {img_key}")
                corrupted = 0
                for i in range(len(img_data)):
                    try:
                        # 尝试解码
                        nparr = np.frombuffer(img_data[i], np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if img is None:
                            corrupted += 1
                    except Exception:
                        corrupted += 1
                
                if corrupted > 0:
                    print(f"    - [ERROR] {corrupted} corrupted images found!")
                else:
                    print(f"    - [OK] All images decodable.")

    except Exception as e:
        print(f"  [ERROR] Failed to read HDF5: {e}")

def main():
    parser = argparse.ArgumentParser(description="Analyze HDF5 datasets for recording quality.")
    parser.add_argument("path", help="Path to a .hdf5 file or a directory containing .hdf5 files")
    parser.add_argument("--recursive", "-r", action="store_true", help="Search directories recursively")
    args = parser.parse_args()

    hdf5_files = []
    if os.path.isdir(args.path):
        if args.recursive:
            for root, dirs, files in os.walk(args.path):
                for f in files:
                    if f.endswith('.hdf5'):
                        hdf5_files.append(os.path.join(root, f))
        else:
            hdf5_files = [os.path.join(args.path, f) for f in os.listdir(args.path) if f.endswith('.hdf5')]
    elif os.path.isfile(args.path):
        hdf5_files = [args.path]
    else:
        print(f"Path not found: {args.path}")
        return

    if not hdf5_files:
        print("No HDF5 files found.")
        return

    print(f"Found {len(hdf5_files)} files. Starting analysis...")
    for f in sorted(hdf5_files):
        analyze_hdf5(f)

if __name__ == "__main__":
    main()
