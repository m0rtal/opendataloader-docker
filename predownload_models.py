from huggingface_hub import snapshot_download

# Docling models used by opendataloader-pdf-hybrid
snapshot_download('docling-project/docling-models', repo_type='model', revision='fc0f2d45e2218ea24bce5045f58a389aed16dc23')
print('Docling models cached')
