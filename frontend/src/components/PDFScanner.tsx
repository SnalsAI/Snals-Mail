import { useState, useRef, useEffect } from 'react';
import { Camera, X, Check, RotateCw, Upload, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

interface PDFScannerProps {
  onScan: (file: File) => void;
  onClose: () => void;
}

export default function PDFScanner({ onScan, onClose }: PDFScannerProps) {
  const [isCamera, setIsCamera] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Avvia fotocamera
  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Usa fotocamera posteriore su mobile
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });

      setStream(mediaStream);
      setIsCamera(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Errore accesso fotocamera:', error);
      toast.error('Impossibile accedere alla fotocamera');
    }
  };

  // Ferma fotocamera
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setIsCamera(false);
  };

  // Cattura foto
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Imposta dimensioni canvas uguali al video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Disegna frame corrente sul canvas
    const context = canvas.getContext('2d');
    if (context) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Converti in immagine
      const imageData = canvas.toDataURL('image/jpeg', 0.9);
      setCapturedImage(imageData);
      stopCamera();
    }
  };

  // Ruota immagine
  const rotateImage = () => {
    if (!capturedImage || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    if (!context) return;

    const img = new Image();
    img.onload = () => {
      // Scambia larghezza e altezza per ruotare
      const newWidth = canvas.height;
      const newHeight = canvas.width;

      canvas.width = newWidth;
      canvas.height = newHeight;

      // Ruota 90 gradi
      context.clearRect(0, 0, newWidth, newHeight);
      context.translate(newWidth / 2, newHeight / 2);
      context.rotate((90 * Math.PI) / 180);
      context.drawImage(img, -img.width / 2, -img.height / 2);

      // Salva nuova immagine
      const rotatedImage = canvas.toDataURL('image/jpeg', 0.9);
      setCapturedImage(rotatedImage);
    };

    img.src = capturedImage;
  };

  // Converti immagine in PDF e carica
  const uploadImage = async () => {
    if (!capturedImage) return;

    setIsProcessing(true);

    try {
      // Converti base64 in blob
      const response = await fetch(capturedImage);
      const blob = await response.blob();

      // Crea file
      const file = new File([blob], `scan-${Date.now()}.jpg`, {
        type: 'image/jpeg',
      });

      onScan(file);
      toast.success('Immagine acquisita con successo');
      onClose();
    } catch (error) {
      console.error('Errore upload immagine:', error);
      toast.error('Errore durante il caricamento');
    } finally {
      setIsProcessing(false);
    }
  };

  // Gestisci selezione file
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Verifica tipo file
      if (file.type.startsWith('image/') || file.type === 'application/pdf') {
        onScan(file);
        toast.success('File selezionato');
        onClose();
      } else {
        toast.error('Formato file non supportato');
      }
    }
  };

  // Cleanup quando componente viene smontato
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Camera className="w-6 h-6 text-blue-600" />
            Scanner Documenti
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {!isCamera && !capturedImage && (
            <div className="space-y-4">
              {/* Opzioni di acquisizione */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Usa fotocamera */}
                <button
                  onClick={startCamera}
                  className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-300 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all group"
                >
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors">
                    <Camera className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">Usa Fotocamera</h3>
                  <p className="text-sm text-gray-600 text-center">
                    Scatta una foto del documento
                  </p>
                </button>

                {/* Carica file */}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-300 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all group"
                >
                  <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-purple-200 transition-colors">
                    <Upload className="w-8 h-8 text-purple-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">Carica File</h3>
                  <p className="text-sm text-gray-600 text-center">
                    Seleziona immagine o PDF dal dispositivo
                  </p>
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-1">
                      Formati supportati
                    </h4>
                    <p className="text-sm text-blue-700">
                      Immagini (JPG, PNG) e documenti PDF. Le immagini verranno automaticamente
                      ottimizzate per il caricamento.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Camera view */}
          {isCamera && (
            <div className="relative">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="w-full rounded-lg"
              />

              {/* Overlay griglia */}
              <div className="absolute inset-0 pointer-events-none">
                <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <line x1="33" y1="0" x2="33" y2="100" stroke="white" strokeWidth="0.2" opacity="0.5" />
                  <line x1="66" y1="0" x2="66" y2="100" stroke="white" strokeWidth="0.2" opacity="0.5" />
                  <line x1="0" y1="33" x2="100" y2="33" stroke="white" strokeWidth="0.2" opacity="0.5" />
                  <line x1="0" y1="66" x2="100" y2="66" stroke="white" strokeWidth="0.2" opacity="0.5" />
                </svg>
              </div>
            </div>
          )}

          {/* Captured image preview */}
          {capturedImage && (
            <div className="relative">
              <img
                src={capturedImage}
                alt="Anteprima"
                className="w-full rounded-lg shadow-lg"
              />
            </div>
          )}

          {/* Hidden canvas per elaborazione */}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t bg-gray-50">
          {isCamera && (
            <div className="flex justify-center gap-3">
              <button
                onClick={stopCamera}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-colors"
              >
                Annulla
              </button>
              <button
                onClick={capturePhoto}
                className="px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center gap-2 shadow-lg"
              >
                <Camera className="w-5 h-5" />
                Scatta Foto
              </button>
            </div>
          )}

          {capturedImage && (
            <div className="flex justify-center gap-3">
              <button
                onClick={() => {
                  setCapturedImage(null);
                  startCamera();
                }}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300 transition-colors"
              >
                Rifai
              </button>
              <button
                onClick={rotateImage}
                className="px-6 py-3 bg-purple-100 text-purple-700 rounded-xl font-semibold hover:bg-purple-200 transition-colors flex items-center gap-2"
              >
                <RotateCw className="w-5 h-5" />
                Ruota
              </button>
              <button
                onClick={uploadImage}
                disabled={isProcessing}
                className="px-8 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 transition-colors flex items-center gap-2 shadow-lg disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Caricamento...
                  </>
                ) : (
                  <>
                    <Check className="w-5 h-5" />
                    Conferma
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
