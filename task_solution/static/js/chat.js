let botui;
let initialMessageSent = false;

function initializeChat() {
  // Ensure Vue and BotUI are loaded before initializing BotUI
  if (typeof Vue === 'undefined' || typeof BotUI === 'undefined') {
    console.error('Vue.js or BotUI has not been loaded yet. Retrying...');
    setTimeout(initializeChat, 100); // Retry after a short delay
    return;
  }
  if (typeof marked === 'undefined') {
    console.error('marked.js has not been loaded yet. Retrying...');
    setTimeout(initializeChat, 100); // Retry after a short delay
    return;
  }

  // Initialize BotUI
  botui = new BotUI('botui-app', {
    vue: Vue // BotUI depends on Vue
  });

  // Chat widget and UI elements
  const chatWidget = document.getElementById('chatBotWidget');
  const chatUiContainer = document.getElementById('botui-app');

  // Toggle chat UI visibility
  chatWidget.addEventListener('click', () => {
    const isChatOpen = chatUiContainer.style.display === 'block';
    chatUiContainer.style.display = isChatOpen ? 'none' : 'block';
    if (!isChatOpen && !initialMessageSent) {
      sendWelcomeMessage();
    }
  });

  // Function to send a welcome message
  function sendWelcomeMessage() {
    botui.message.add({
      content: 'こんにちは！何かお手伝いできることはありますか？',
      delay: 300,
      loading: true
    }).then(() => {
      initialMessageSent = true;
      botui.action.text({
        action: {
          placeholder: 'メッセージを入力...'
        }
      }).then(handleUserInput);
    });
  }

  // Function to handle user input
  function handleUserInput(res) {
    const userMessage = res.value;

    let loadingMessagePromise = botui.message.add({
      loading: true,
      content: '考え中...'
    });

    loadingMessagePromise.then(loadingMessageIndex => {
      fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      })
      .then(response => response.json())
      .then(data => {
        // Ensure marked is available before using it
        if (typeof marked === 'function') {
          const htmlReply = marked(data.reply);
          botui.message.update(loadingMessageIndex, {
            loading: false,
            content: htmlReply,
            type: 'html'
          }).then(() => {
            botui.action.text({
              action: {
                placeholder: 'メッセージを入力...'
              }
            }).then(handleUserInput);
          });
        } else {
          // This should ideally not be reached if initializeChat waits for marked
          console.error('marked.js is not loaded or not a function at the time of use.');
          botui.message.update(loadingMessageIndex, {
            loading: false,
            content: data.reply // Fallback to plain text
          }).then(() => {
            botui.action.text({
              action: {
                placeholder: 'メッセージを入力...'
              }
            }).then(handleUserInput);
          });
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        botui.message.update(loadingMessageIndex, {
          loading: false,
          content: '申し訳ありません、エラーが発生しました。'
        }).then(() => {
          botui.action.text({
            action: {
              placeholder: 'メッセージを入力...'
            }
          }).then(handleUserInput);
        });
      });
    });
  }

  // Handle initial chat open state from localStorage
  const chatOpenState = localStorage.getItem('chatOpen');
  if (chatUiContainer && chatOpenState === 'true') { // Ensure chatUiContainer exists
    chatUiContainer.style.display = 'block';
    if (!initialMessageSent) {
      sendWelcomeMessage(); // Assumes botui is initialized by now
    }
  } else if (chatUiContainer) { // Ensure chatUiContainer exists
    chatUiContainer.style.display = 'none';
  }

  window.addEventListener('beforeunload', () => {
    if (chatUiContainer) { // Ensure chatUiContainer exists
      const isChatOpen = chatUiContainer.style.display === 'block';
      localStorage.setItem('chatOpen', isChatOpen);
    }
  });

  console.log("Chat initialized successfully.");
}

document.addEventListener('DOMContentLoaded', () => {
  let attempts = 0;
  const maxAttempts = 100; // Try for 10 seconds (100 * 100ms)
  const interval = 100; // 100ms
  let markedWasFunctionAtLeastOnce = false;

  function checkDependenciesAndInit() {
    if (typeof marked === 'function') {
      markedWasFunctionAtLeastOnce = true;
    }

    if (typeof Vue !== 'undefined' && typeof BotUI !== 'undefined' && typeof marked === 'function') {
      console.log("All dependencies (Vue, BotUI, marked) loaded and marked is a function.");
      initializeChat();
    } else {
      attempts++;
      if (attempts < maxAttempts) {
        if (typeof Vue === 'undefined') console.log("Vue not loaded yet. Attempt: ", attempts);
        if (typeof BotUI === 'undefined') console.log("BotUI not loaded yet. Attempt: ", attempts);
        if (typeof marked !== 'function') console.log("marked is not a function yet. typeof marked:", typeof marked, ". Attempt: ", attempts);
        setTimeout(checkDependenciesAndInit, interval);
      } else {
        console.error(`Failed to load all dependencies (Vue, BotUI, marked as function) after ${maxAttempts} attempts. Chat initialization aborted. Last typeof marked: ${typeof marked}. Was marked ever a function during polling: ${markedWasFunctionAtLeastOnce}`);
      }
    }
  }
  checkDependenciesAndInit();
});
