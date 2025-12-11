import { useEffect, useState } from 'react';

interface PWAInstallPrompt extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

interface PWAStatus {
  isInstalled: boolean;
  isInstallable: boolean;
  isOnline: boolean;
  canInstall: boolean;
  registration: ServiceWorkerRegistration | null;
}

interface UsePWAReturn extends PWAStatus {
  install: () => Promise<void>;
  requestNotificationPermission: () => Promise<NotificationPermission>;
  subscribe: () => Promise<PushSubscription | null>;
  unsubscribe: () => Promise<boolean>;
  clearCache: () => Promise<void>;
}

export function usePWA(): UsePWAReturn {
  const [installPrompt, setInstallPrompt] = useState<PWAInstallPrompt | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  // Registra Service Worker
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/service-worker.js')
        .then((reg) => {
          console.log('✅ Service Worker registrato:', reg.scope);
          setRegistration(reg);

          // Controlla aggiornamenti ogni 30 minuti
          setInterval(() => {
            reg.update();
          }, 30 * 60 * 1000);
        })
        .catch((error) => {
          console.error('❌ Errore registrazione Service Worker:', error);
        });
    }
  }, []);

  // Controlla se l'app è già installata
  useEffect(() => {
    const checkInstallation = () => {
      const isStandalone =
        window.matchMedia('(display-mode: standalone)').matches ||
        (window.navigator as any).standalone ||
        document.referrer.includes('android-app://');

      setIsInstalled(isStandalone);
    };

    checkInstallation();
    window.addEventListener('appinstalled', checkInstallation);

    return () => {
      window.removeEventListener('appinstalled', checkInstallation);
    };
  }, []);

  // Ascolta evento beforeinstallprompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as PWAInstallPrompt);
      console.log('📱 App installabile!');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Monitora stato online/offline
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      console.log('🟢 Connessione ripristinata');
    };

    const handleOffline = () => {
      setIsOnline(false);
      console.log('🔴 Connessione persa');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Installa PWA
  const install = async () => {
    if (!installPrompt) {
      console.warn('⚠️ Nessun prompt di installazione disponibile');
      return;
    }

    try {
      await installPrompt.prompt();
      const { outcome } = await installPrompt.userChoice;

      if (outcome === 'accepted') {
        console.log('✅ Utente ha accettato l\'installazione');
      } else {
        console.log('❌ Utente ha rifiutato l\'installazione');
      }

      setInstallPrompt(null);
    } catch (error) {
      console.error('❌ Errore durante installazione:', error);
    }
  };

  // Richiedi permesso notifiche
  const requestNotificationPermission = async (): Promise<NotificationPermission> => {
    if (!('Notification' in window)) {
      console.warn('⚠️ Notifiche non supportate');
      return 'denied';
    }

    if (Notification.permission === 'granted') {
      console.log('✅ Permesso notifiche già concesso');
      return 'granted';
    }

    try {
      const permission = await Notification.requestPermission();
      console.log(`📢 Permesso notifiche: ${permission}`);
      return permission;
    } catch (error) {
      console.error('❌ Errore richiesta permesso notifiche:', error);
      return 'denied';
    }
  };

  // Sottoscrivi a push notifications
  const subscribe = async (): Promise<PushSubscription | null> => {
    if (!registration) {
      console.warn('⚠️ Service Worker non registrato');
      return null;
    }

    try {
      const permission = await requestNotificationPermission();
      if (permission !== 'granted') {
        console.warn('⚠️ Permesso notifiche negato');
        return null;
      }

      // VAPID public key (da generare sul backend)
      const vapidPublicKey = 'YOUR_VAPID_PUBLIC_KEY_HERE';

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });

      console.log('✅ Sottoscritto a push notifications');

      // Invia subscription al backend
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription),
      });

      return subscription;
    } catch (error) {
      console.error('❌ Errore sottoscrizione push:', error);
      return null;
    }
  };

  // Annulla sottoscrizione
  const unsubscribe = async (): Promise<boolean> => {
    if (!registration) return false;

    try {
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();

        // Notifica il backend
        await fetch('/api/push/unsubscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });

        console.log('✅ Annullata sottoscrizione push');
        return true;
      }
      return false;
    } catch (error) {
      console.error('❌ Errore annullamento sottoscrizione:', error);
      return false;
    }
  };

  // Cancella cache
  const clearCache = async () => {
    if (!registration) return;

    try {
      const messageChannel = new MessageChannel();

      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          console.log('✅ Cache cancellata');
        }
      };

      registration.active?.postMessage(
        { type: 'CLEAR_CACHE' },
        [messageChannel.port2]
      );
    } catch (error) {
      console.error('❌ Errore cancellazione cache:', error);
    }
  };

  return {
    isInstalled,
    isInstallable: !!installPrompt,
    isOnline,
    canInstall: !!installPrompt && !isInstalled,
    registration,
    install,
    requestNotificationPermission,
    subscribe,
    unsubscribe,
    clearCache,
  };
}

// Utility per convertire VAPID key
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}
