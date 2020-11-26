# Neigh

## TODO

- [X] Set up a virtual environment and requirements.txt
- [X] Use https://python-sounddevice.readthedocs.io/en/0.3.15/ over pysound
- [X] Separate out recording module?

## Raspberry PI Notes

Get the proper TF release from here first https://github.com/lhelontra/tensorflow-on-arm/releases (match "cp" with your python version). Install with `pip3 install file.whl`.

Next, install the repo version of `h5py` because the pip version doesn't work properly:

`sudo apt-get install python3-h5py`

Install the correct version of LLVM:

```sh
sudo apt install llvm-8
export LLVM_CONFIG=/usr/bin/llvm-config-8
pip3 install -r requirements.txt
```

Intiface server *must* be run with sudo to be able to use bluetooth, this is just how Linux works.

All `pip` commands need to be run as `pip3` even when the venv is activated.
