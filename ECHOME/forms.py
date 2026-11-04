
from django import forms


class TimeCapsuleForm(forms.Form):

    # Encrypted file received from the browser
    encrypted_file = forms.FileField(
        required=True,
        error_messages={
            "required": "No encrypted file was uploaded.",
            "invalid": "Invalid file upload.",
        }
    )

    # File metadata
    file_ext = forms.CharField(
        max_length=10,
        required=True,
        strip=True,
        error_messages={
            "required": "File extension is required.",
        }
    )

    file_mime = forms.CharField(
        max_length=20,
        required=True,
        strip=True,
        error_messages={
            "required": "File MIME type is required.",
        }
    )

    # Capsule details
    unlock_time = forms.IntegerField(
        min_value=1,
        required=True,
        error_messages={
            "required": "Unlock time is required.",
            "invalid": "Unlock time must be a valid integer.",
            "min_value": "Unlock time must be greater than zero.",
        }
    )

    email = forms.EmailField(
        max_length=254,
        required=True,
        error_messages={
            "required": "Recipient email is required.",
            "invalid": "Enter a valid email address.",
        }
    )

    decryption_password = forms.CharField(
        max_length=255,
        required=True,
        strip=False,
        error_messages={
            "required": "Decryption password is required.",
        }
    )

    def clean_encrypted_file(self):
        uploaded_file = self.cleaned_data["encrypted_file"]

        if uploaded_file.size == 0:
            raise forms.ValidationError("Uploaded file is empty.")

        return uploaded_file

    def clean_file_ext(self):
        ext = self.cleaned_data["file_ext"].lstrip(".").lower()

        if not ext:
            raise forms.ValidationError("File extension is required.")

        return ext

    def clean_file_mime(self):
        mime = self.cleaned_data["file_mime"].lower()

        if "/" not in mime:
            raise forms.ValidationError("Invalid MIME type.")

        return mime
