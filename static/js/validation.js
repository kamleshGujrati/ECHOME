document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll("input, textarea").forEach(field => {

        field.addEventListener("input", () => {

            validateField(field);

        });

    });

});

function validateField(field){

    const value = field.value.trim();

    clearError(field);

    if(field.hasAttribute("required") && value === ""){

        showError(field,"This field is required.");

        return false;

    }

    if(field.type === "email"){

        const emailPattern =
            /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if(value !== "" && !emailPattern.test(value)){

            showError(field,"Enter a valid email.");

            return false;

        }

    }

    if(field.name === "username"){

        if(value.length < 4){

            showError(field,"Username must be at least 4 characters.");

            return false;

        }

    }

    if(field.name === "password"){

        if(value.length < 8){

            showError(field,"Password must be at least 8 characters.");

            return false;

        }

    }

    if(field.name === "confirm"){

        const password =
            document.querySelector("[name='password']");

        if(password && value !== password.value){

            showError(field,"Passwords do not match.");

            return false;

        }

    }

    field.style.borderColor = "green";

    return true;

}

function showError(field,message){

    field.style.borderColor = "red";

    let error =
        field.nextElementSibling;

    if(error && error.classList.contains("error")){

        error.textContent = message;

        return;

    }

    error = document.createElement("div");

    error.className = "error";

    error.textContent = message;

    field.after(error);

}

function clearError(field){

    field.style.borderColor = "#ccc";

    const error =
        field.nextElementSibling;

    if(error && error.classList.contains("error")){

        error.remove();

    }

}