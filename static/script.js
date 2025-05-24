document.addEventListener("DOMContentLoaded", () => {
  // Get DOM elements
  const directionInput = document.getElementById("direction")
  const languageOptions = document.querySelectorAll(".language-option")
  const swapBtn = document.getElementById("swapBtn")
  const inputText = document.getElementById("inputText")
  const charCount = document.getElementById("charCount")
  const clearBtn = document.getElementById("clearBtn")
  const copyBtn = document.getElementById("copyBtn")
  const translateBtn = document.getElementById("translateBtn")
  const translatorForm = document.getElementById("translatorForm")
  const inputLabel = document.getElementById("inputLabel")
  const outputLabel = document.getElementById("outputLabel")
  const outputText = document.getElementById("outputText")

  // Language mappings
  const languages = {
    en2fr: { input: "English", output: "French", inputFlag: "🇺🇸", outputFlag: "🇫🇷" },
    fr2en: { input: "French", output: "English", inputFlag: "🇫🇷", outputFlag: "🇺🇸" },
  }

  // Initialize the interface
  function init() {
    const currentDirection = directionInput.value || "en2fr"
    updateInterface(currentDirection)
    updateCharCount()
  }

  // Update interface based on direction
  function updateInterface(direction) {
    const lang = languages[direction]

    // Update labels
    inputLabel.textContent = lang.input
    outputLabel.textContent = lang.output

    // Update language options
    languageOptions.forEach((option) => {
      option.classList.remove("active")
      if (option.dataset.direction === direction) {
        option.classList.add("active")
      }
    })

    // Update placeholder
    inputText.placeholder = `Enter ${lang.input.toLowerCase()} text to translate...`

    // Update direction input
    directionInput.value = direction
  }

  // Handle language option clicks
  languageOptions.forEach((option) => {
    option.addEventListener("click", function () {
      const direction = this.dataset.direction
      updateInterface(direction)
      inputText.focus()
    })
  })

  // Handle swap button
  swapBtn.addEventListener("click", function () {
    const currentDirection = directionInput.value
    const newDirection = currentDirection === "en2fr" ? "fr2en" : "en2fr"

    // Swap the text if there's content
    const currentText = inputText.value.trim()
    const translatedText = outputText.textContent.trim()

    if (translatedText && translatedText !== "Translation will appear here...") {
      inputText.value = translatedText
      outputText.innerHTML = '<span class="placeholder">Translation will appear here...</span>'
    }

    updateInterface(newDirection)
    updateCharCount()
    inputText.focus()

    // Add animation
    this.style.transform = "rotate(180deg)"
    setTimeout(() => {
      this.style.transform = ""
    }, 300)
  })

  // Handle character count
  function updateCharCount() {
    const count = inputText.value.length
    charCount.textContent = count

    // Change color based on limit
    if (count > 450) {
      charCount.style.color = "#e53e3e"
    } else if (count > 400) {
      charCount.style.color = "#dd6b20"
    } else {
      charCount.style.color = "#718096"
    }
  }

  inputText.addEventListener("input", updateCharCount)

  // Handle clear button
  clearBtn.addEventListener("click", () => {
    inputText.value = ""
    outputText.innerHTML = '<span class="placeholder">Translation will appear here...</span>'
    updateCharCount()
    inputText.focus()

    // Hide copy button if it exists
    if (copyBtn) {
      copyBtn.style.display = "none"
    }
  })

  // Handle copy button
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const textToCopy = outputText.textContent

      if (navigator.clipboard) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          showToast("Text copied to clipboard!")
        })
      } else {
        // Fallback for older browsers
        const textArea = document.createElement("textarea")
        textArea.value = textToCopy
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand("copy")
        document.body.removeChild(textArea)
        showToast("Text copied to clipboard!")
      }
    })
  }

  // Handle form submission
  translatorForm.addEventListener("submit", (e) => {
    const text = inputText.value.trim()

    if (!text) {
      e.preventDefault()
      showToast("Please enter some text to translate.")
      inputText.focus()
      return
    }

    // Show loading state
    translateBtn.classList.add("loading")
    translateBtn.disabled = true

    // The form will submit normally, but we show loading state
  })

  // Auto-resize textarea
  inputText.addEventListener("input", function () {
    this.style.height = "auto"
    this.style.height = Math.min(this.scrollHeight, 200) + "px"
  })

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl/Cmd + Enter to translate
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault()
      translatorForm.submit()
    }

    // Ctrl/Cmd + K to focus input
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault()
      inputText.focus()
    }

    // Escape to clear
    if (e.key === "Escape" && document.activeElement === inputText) {
      clearBtn.click()
    }
  })

  // Toast notification function
  function showToast(message) {
    // Remove existing toast
    const existingToast = document.querySelector(".toast")
    if (existingToast) {
      existingToast.remove()
    }

    // Create toast
    const toast = document.createElement("div")
    toast.className = "toast"
    toast.textContent = message
    toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #48bb78;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `

    document.body.appendChild(toast)

    // Remove after 3 seconds
    setTimeout(() => {
      toast.style.animation = "slideOut 0.3s ease"
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove()
        }
      }, 300)
    }, 3000)
  }

  // Add CSS for toast animations
  const style = document.createElement("style")
  style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `
  document.head.appendChild(style)

  // Initialize the app
  init()

  // Add fade-in animation to main container
  document.querySelector(".translator-container").classList.add("fade-in")
})
