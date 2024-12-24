from transformers import AutoTokenizer

# Tải tokenizer của mô hình
tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")

# Kiểm tra độ dài tối đa của input
max_length = tokenizer.model_max_length

print(f"Độ dài tối đa của đầu vào cho mô hình: {max_length} tokens")
