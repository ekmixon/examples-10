import os
import shutil
import zipfile
import argparse
from pathlib2 import Path
import wget
import tensorflow as tf


def check_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return Path(path).resolve(strict=False)


def download(source, target, force_clear=False):
    if force_clear and os.path.exists(target):
        print(f'Removing {target}...')
        shutil.rmtree(target)

    check_dir(target)

    targt_file = str(Path(target).joinpath('data.zip'))
    if os.path.exists(targt_file) and not force_clear:
        print('data already exists, skipping download')
        return

    if source.startswith('http'):
        print(f"Downloading from {source} to {target}")
        wget.download(source, targt_file)
        print("Done!")
    else:
        print(f"Copying from {source} to {target}")
        shutil.copyfile(source, targt_file)

    print(f'Unzipping {targt_file}')
    zipr = zipfile.ZipFile(targt_file)
    zipr.extractall(target)
    zipr.close()


def process_image(path, image_size=160):
    img_raw = tf.io.read_file(path)
    img_tensor = tf.image.decode_jpeg(img_raw, channels=3)
    return tf.image.resize(img_tensor, [image_size, image_size]) / 255


def walk_images(path, image_size=160):
    imgs = []
    print(f'Scanning {path}')
    # find subdirectories in base path
    # (they should be the labels)
    labels = []
    for (_, dirs, _) in os.walk(path):
        print(f'Found {dirs}')
        labels = dirs
        break

    for d in labels:
        tmp_path = os.path.join(path, d)
        print(f'Processing {tmp_path}')
        # only care about files in directory
        for item in os.listdir(tmp_path):
            if not item.lower().endswith('.jpg'):
                print(f'skipping {item}')
                continue

            image = os.path.join(tmp_path, item)
            try:
                img = process_image(image, image_size)
                assert img.shape[2] == 3, "Invalid channel count"
                # write out good images
                imgs.append(image)
            except img.shape[2] != 3:
                print(f'{image}\n')

    return imgs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='data cleaning for binary image task')
    parser.add_argument('-b', '--base_path',
                        help='directory to base data', default='../../data')
    parser.add_argument(
        '-d', '--data', help='directory to training data', default='train')
    parser.add_argument(
        '-t', '--target', help='target file to hold good data', default='train.txt')  # noqa: E501
    parser.add_argument(
        '-i', '--img_size', help='target image size to verify', default=160, type=int)  # noqa: E501
    parser.add_argument(
        '-z', '--zipfile', help='source data zip file', default='../../tacodata.zip')  # noqa: E501
    parser.add_argument('-f', '--force',
                        help='force clear all data', default=False, action='store_true')  # noqa: E501
    args = parser.parse_args()
    print(args)

    print(f'Using TensorFlow v.{tf.__version__}')

    base_path = Path(args.base_path).resolve(strict=False)
    print(f'Base Path:  {base_path}')
    data_path = base_path.joinpath(args.data).resolve(strict=False)
    print(f'Train Path: {data_path}')
    target_path = Path(base_path).resolve(strict=False).joinpath(args.target)
    print(f'Train File: {target_path}')
    zip_path = args.zipfile

    print('Acquiring data...')
    download('https://aiadvocate.blob.core.windows.net/public/tacodata.zip',
             str(base_path), args.force)

    if os.path.exists(str(target_path)):
        print('dataset text file already exists, skipping check')
    else:
        print('Testing images...')
        images = walk_images(str(data_path), args.img_size)

        # save file
        print(f'writing dataset to {target_path}')
        with open(str(target_path), 'w+') as f:
            f.write('\n'.join(images))
