from huggingface_hub import snapshot_download
snapshot_download('ds4sd/docling-models', repo_type='model')
print('Docling models cached')