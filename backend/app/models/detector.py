import torch
from huggingface_hub import PyTorchModelHubMixin
from fairseq.models.wav2vec import Wav2Vec2Model, Wav2Vec2Config


class ModelSSL(torch.nn.Module):
    def __init__(self):
        super().__init__()
        cfg = Wav2Vec2Config(
            encoder_layers=12,
            encoder_embed_dim=768,
            quantize_targets=True,
            latent_dim=256,
            final_dim=256,
        )
        self.model = Wav2Vec2Model(cfg)

    def extract_feature(self, input_data, device):
        if input_data.ndim == 3:
            input_data = input_data[:, :, 0]
        with torch.no_grad():
            features = self.model(input_data.to(device), mask=False, features_only=True)["x"]
        return features


class detectorDeepfake(torch.nn.Module, PyTorchModelHubMixin):
    def __init__(self, device="cpu"):
        super().__init__()
        self.device = device
        self.ssl_orig_output_dim = 768
        self.num_classes = 2
        self.m_ssl = ModelSSL()
        self.adap_pool_1d = torch.nn.AdaptiveAvgPool1d(output_size=1)
        self.proj_fc = torch.nn.Linear(
            in_features=self.ssl_orig_output_dim,
            out_features=self.num_classes,
        )

    def forward(self, wav):
        emb = self.m_ssl.extract_feature(wav, self.device)
        emb = emb.transpose(1, 2)
        pooled_emb = self.adap_pool_1d(emb)
        pooled_emb = pooled_emb.squeeze(-1)
        logits = self.proj_fc(pooled_emb)
        return logits