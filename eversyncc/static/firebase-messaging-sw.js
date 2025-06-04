importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyCR9FFFiNFt6ORYu7KJHv_fT-aD2fW7bIg",
  authDomain: "eversync333.firebaseapp.com",
  projectId: "eversync333",
  messagingSenderId: "546896423149",
  appId: "1:546896423149:web:c06d07957a7080965144e4",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    click_action: 'https://eversync.fly.dev'
  };

  self.registration.showNotification(notificationTitle,
    notificationOptions);
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('https://eversync.fly.dev')
  );
});