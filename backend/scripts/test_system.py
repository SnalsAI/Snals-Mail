#!/usr/bin/env python3
"""
Script di test sistema completo SNALS Email Agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import requests
import time
from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import Email, EmailCategory, AccountType, EmailStatus
from app.services.categorizer import EmailCategorizer
from app.services.interpreter import EmailInterpreter
from datetime import datetime

settings = get_settings()


def test_api_health():
    """Test health check API"""
    print("\n🔍 Test 1: API Health Check")
    try:
        response = requests.get(f"http://localhost:{settings.API_PORT}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ API risponde: {response.json()}")
            return True
        else:
            print(f"   ❌ API errore: status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Errore connessione API: {e}")
        return False


def test_database():
    """Test connessione database"""
    print("\n🔍 Test 2: Database Connection")
    try:
        db = SessionLocal()
        # Test query
        count = db.query(Email).count()
        print(f"   ✅ Database connesso. Email presenti: {count}")
        db.close()
        return True
    except Exception as e:
        print(f"   ❌ Errore database: {e}")
        return False


def test_llm_categorizer():
    """Test categorizzatore LLM"""
    print("\n🔍 Test 3: LLM Categorizer")
    try:
        categorizer = EmailCategorizer()
        
        # Email di test
        test_email = {
            'mittente': 'test@scuola.it',
            'oggetto': 'Convocazione RSU per riunione urgente',
            'corpo': 'Si convoca per il giorno 15 novembre alle ore 15:00 la riunione delle RSU.'
        }
        
        categoria, confidence = categorizer.categorize(
            mittente=test_email['mittente'],
            oggetto=test_email['oggetto'],
            corpo=test_email['corpo']
        )
        
        print(f"   ✅ Categorizzazione completata:")
        print(f"      Categoria: {categoria.value}")
        print(f"      Confidence: {confidence:.2f}")
        return True
        
    except Exception as e:
        print(f"   ❌ Errore categorizzatore: {e}")
        return False


def test_llm_interpreter():
    """Test interpretatore LLM"""
    print("\n🔍 Test 4: LLM Interpreter")
    try:
        interpreter = EmailInterpreter()
        
        result = interpreter.interpret(
            categoria=EmailCategory.CONVOCAZIONE_SCUOLA,
            mittente='scuola@example.it',
            oggetto='Convocazione RSU',
            corpo='Riunione il 15/11/2025 alle 15:00 in sala docenti',
            allegati=[],
            data_oggi=datetime.now().isoformat()
        )
        
        print(f"   ✅ Interpretazione completata:")
        print(f"      Dati estratti: {list(result.keys())}")
        return True
        
    except Exception as e:
        print(f"   ❌ Errore interpretatore: {e}")
        return False


def test_save_email():
    """Test salvataggio email in database"""
    print("\n🔍 Test 5: Salvataggio Email")
    try:
        db = SessionLocal()
        
        # Crea email di test
        email = Email(
            message_id=f"test-{int(time.time())}@test.local",
            account_type=AccountType.NORMALE,
            mittente="test@example.com",
            destinatario="snals@example.com",
            oggetto="Email di test",
            corpo="Questo è un test del sistema",
            data_ricezione=datetime.now(),
            categoria=EmailCategory.INFO_GENERICHE,
            categoria_confidence=0.95,
            stato=EmailStatus.CATEGORIZZATA
        )
        
        db.add(email)
        db.commit()
        
        print(f"   ✅ Email salvata con ID: {email.id}")
        
        # Cleanup
        db.delete(email)
        db.commit()
        db.close()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Errore salvataggio: {e}")
        return False


def main():
    """Esegue tutti i test"""
    print("="*60)
    print("🧪 SNALS Email Agent - Test Sistema Completo")
    print("="*60)
    
    results = []
    
    # Esegui test
    results.append(("API Health", test_api_health()))
    results.append(("Database", test_database()))
    results.append(("LLM Categorizer", test_llm_categorizer()))
    results.append(("LLM Interpreter", test_llm_interpreter()))
    results.append(("Save Email", test_save_email()))
    
    # Riepilogo
    print("\n" + "="*60)
    print("📊 RIEPILOGO TEST")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name:20s} {status}")
    
    print(f"\n   Totale: {passed}/{total} test passati")
    
    if passed == total:
        print("\n🎉 Tutti i test sono passati!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test falliti")
        return 1


if __name__ == "__main__":
    sys.exit(main())
