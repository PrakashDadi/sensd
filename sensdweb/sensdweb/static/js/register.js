const usernameFeild = document.querySelector("#usernameFeild");
const feedbackArea = document.querySelector('.invalid_feedback');
const emailFeild = document.querySelector('#emailFeild');
const emailfeedbackArea = document.querySelector('.invalid_emailfeedback');
const usernamesuccess = document.querySelector('.usernamesuccess');
const emailsuccess = document.querySelector('.emailsuccess');
const floatingPasswordFeild = document.querySelector('#floatingPasswordFeild')
const showPasswordToggle = document.querySelector('.showPasswordToggle')
const submitBtn = document.querySelector('.submit-btn')



usernameFeild.addEventListener("keyup", (e) => {
  console.log("working", e.target.value)
  const usernameVal = e.target.value;
  usernamesuccess.style.display = "none";
  usernameFeild.classList.remove("is-invalid");
  feedbackArea.style.display = "none";
  feedbackArea.innerHTML = "";

  if (usernameVal.length > 0) {
    usernamesuccess.style.display = "block";
    usernamesuccess.textContent = `Checking ${usernameVal}`;
    fetch("/authentication/validate-username", {
      method: "POST",
      body: JSON.stringify({ username: usernameVal }),
    })
      .then((res) => res.json())
      .then((data) => {
        usernamesuccess.style.display = "none";
        if (data.username_error) {      
          submitBtn.disabled = true;
          usernameFeild.classList.add("is-invalid");
          feedbackArea.style.display = "block";
          feedbackArea.innerHTML += `<p>${data.username_error}</p>`
        } else {
          submitBtn.disabled = false;
          usernamesuccess.style.display = "block";
          usernamesuccess.textContent = `Username Available`;
        }
      });
  }
});

emailFeild.addEventListener("keyup", (e) => {
    const emailVal = e.target.value;
    emailsuccess.style.display = "none";
    emailFeild.classList.remove("is-invalid");
    emailfeedbackArea.style.display = "none";
    emailfeedbackArea.innerHTML = "";
  
    if (emailVal.length > 0) {
      emailsuccess.style.display = "block";
      // emailsuccess.textContent = `Checking ${emailVal}`;
      fetch("/authentication/validate-email", {
        method: "POST",
        body: JSON.stringify({ email: emailVal }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.email_error) {
            submitBtn.disabled = true;
            emailFeild.classList.add("is-invalid");
            emailfeedbackArea.style.display = "block";
            emailfeedbackArea.innerHTML += `<p>${data.email_error}</p>`
          } else {
            submitBtn.disabled = false;
            emailsuccess.style.display = "block";
            emailsuccess.textContent = `Email Available`;
          }
        });
    }
  });
