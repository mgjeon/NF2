# Neural Network Force-Free magnetic field extrapolation - NF2

```
git clone https://github.com/mgjeon/NF2
cd NF2
git remote add upstream https://github.com/RobertJaro/NF2
git checkout learn
git fetch upstream
git merge upstream/main
git push origin learn
```

```
mamba create -n nf2
mamba activate nf2
mamba update -y mamba
mamba install -y python=3.10 ipykernel
pip install --upgrade pip
mamba install -y pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
mamba install -y lightning numpy scipy matplotlib sunpy astropy wandb scikit-image scikit-learn tqdm gdown ipywidgets

pip install -e .
```

