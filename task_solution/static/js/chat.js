let botui;
let initialMessageSent = false;

document.addEventListener('DOMContentLoaded', () => {
  // Ensure Vue and BotUI are loaded before initializing BotUI
  if (typeof Vue === 'undefined' || typeof BotUI === 'undefined') {
    console.error('Vue.js or BotUI has not been loaded yet.');
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
          console.error('marked.js is not loaded or not a function.');
          // Fallback to plain text if marked is not available
          botui.message.update(loadingMessageIndex, {
            loading: false,
            content: data.reply // Display as plain text
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
  if (chatOpenState === 'true') {
    chatUiContainer.style.display = 'block';
    if (!initialMessageSent) {
      // Ensure BotUI is initialized before sending welcome message
      if (botui) {
        sendWelcomeMessage();
      } else {
        // This case should ideally not happen if DOMContentLoaded waits for all scripts
        console.warn("BotUI not ready when trying to send welcome message from localStorage state.");
      }
    }
  } else {
    chatUiContainer.style.display = 'none';
  }

  window.addEventListener('beforeunload', () => {
    const isChatOpen = chatUiContainer.style.display === 'block';
    localStorage.setItem('chatOpen', isChatOpen);
  });
});
