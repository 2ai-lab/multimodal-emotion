import warnings

warnings.filterwarnings("ignore")


import torch
import torchaudio
import os
import librosa
from IPython.display import Audio
import librosa
from torchaudio.utils import download_asset
import cv2
import glob
import pandas as pd


from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
import torch.nn.functional as F
from torch import nn
import torch
import torch.optim as optim
import lightning.pytorch as pl
from torchaudio.transforms import *
import numpy as np
import torchmetrics
from lightning.pytorch.loggers import CSVLogger
from torch.nn.utils.rnn import pad_sequence
import re
from transformers import AutoFeatureExtractor, ASTForAudioClassification
import configparser
from torch.utils.data import DataLoader
from emotion_utils.utils.utils import *
from emotion_utils.utils.models import *


def get_model(model_name, **kwargs):
    model_dict = {
            "audio": AudioSpectrogramModel ,
            "text": LangModel,
            "multimodal": AudioLangModel,
            }
    return model_dict[model_name](**kwargs)

def generate_sample_weights(meta_df, label="category"):
    class_counts = meta_df.category.value_counts()
    sample_weights = [1 / class_counts[i] for i in meta_df[label].values]
    return sample_weights

def main():
    args = ArgParser()

    config = configparser.ConfigParser()
    config.read(args.config_path)

    BATCH_SIZE = args.batch_size 
    MAX_EPOCH = args.max_epoch
    llogger = CSVLogger("emotions", args.log_dir)


    data_path = config["data"]["audio"]
    cat_df = get_meta(config["data"]["label"], "category")
    dial_df = get_meta(config["data"]["text"], "dial")
    meta_df = (
        pd.merge(cat_df, dial_df, on="file")
        .groupby(["file", "dial"])
        .head(1)
        .reset_index()
        .drop(columns=["index"])
    )
    meta_df["category"] = meta_df["category"].str.replace(";.*", "", regex=True)
    model = get_model(args.model_name, **config["model"])
    dataset = AudioDataset(meta_df, data_path, modality="text")

    train_set, val_set = torch.utils.data.random_split(
        dataset,
        [0.8, 0.2],
    )

    train_dataloader = DataLoader(
        train_set,
        batch_size=BATCH_SIZE,
        num_workers=args.num_workers,
        drop_last=True,
        sampler=generate_sample_weights(meta_df),
    )

    test_dataloader = DataLoader(
        val_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=args.num_workers, drop_last=True
    )


    trainer = pl.Trainer(
        max_epochs=MAX_EPOCH,
        gradient_clip_val=0,
        logger=llogger,
    )

    trainer.fit(
        model,
        train_dataloader,
        test_dataloader,
    )

if __name__ == "__main__":
    main()
