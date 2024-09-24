from cryptography.fernet import Fernet


def generate_key():
    return Fernet.generate_key()


def encrypt_file(file_content, key):
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(file_content)
    return encrypted_data


def decrypt_file(encrypted_data, key):
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data)
    return decrypted_data
