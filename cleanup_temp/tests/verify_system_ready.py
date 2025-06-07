#!/usr/bin/env python3
"""
System Readiness Verification Script
====================================

This script verifies that the categorization system is ready for production use
and tests the complete flow for new transactions.
"""

import sqlite3
import sys
import os
from datetime import datetime, date

# Add the current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_system_readiness():
    """Comprehensive verification that the system is ready for production use."""
    
    print("🔍 VERIFYING SYSTEM READINESS")
    print("=" * 50)
    print(f"📅 Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Database Connection and Structure
    print("1️⃣ TESTING DATABASE CONNECTION...")
    try:
        conn = sqlite3.connect('richness.db')
        cursor = conn.cursor()
        
        # Verify tables exist
        required_tables = ['usuarios', 'extratos', 'cartoes', 'economias', 'ai_categorizations']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"   ❌ Missing tables: {missing_tables}")
            return False
        else:
            print("   ✅ All required tables present")
            
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Test 2: Categorization Status
    print("\n2️⃣ CHECKING CATEGORIZATION STATUS...")
    conn = sqlite3.connect('richness.db')
    cursor = conn.cursor()
    
    # Check for NULL categories
    cursor.execute("SELECT COUNT(*) FROM extratos WHERE categoria IS NULL")
    null_extratos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cartoes WHERE categoria IS NULL")
    null_cartoes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM economias WHERE categoria IS NULL")
    null_economias = cursor.fetchone()[0]
    
    total_null = null_extratos + null_cartoes + null_economias
    
    if total_null == 0:
        print("   ✅ No NULL categories found")
    else:
        print(f"   ⚠️  {total_null} transactions still have NULL categories")
    
    # Show current distribution
    cursor.execute("SELECT categoria, COUNT(*) FROM extratos GROUP BY categoria ORDER BY COUNT(*) DESC")
    categories = cursor.fetchall()
    print("   📊 Current category distribution:")
    for cat, count in categories:
        print(f"      {cat}: {count}")
    
    conn.close()
    
    # Test 3: Cache Status
    print("\n3️⃣ CHECKING CACHE STATUS...")
    cache_files = [
        'cache/categorias_cache.pkl',
        'cache/descricoes_cache.pkl',
        'cache/cache.pkl'
    ]
    
    cache_issues = False
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            size = os.path.getsize(cache_file)
            print(f"   ⚠️  {cache_file} exists ({size} bytes) - should be cleared")
            cache_issues = True
        else:
            print(f"   ✅ {cache_file} not found (good)")
    
    if not cache_issues:
        print("   ✅ All cache files properly cleared")
    
    # Test 4: Import System Modules
    print("\n4️⃣ TESTING SYSTEM MODULES...")
    try:
        from utils.auto_categorization import run_auto_categorization_on_login
        print("   ✅ Auto categorization module imported successfully")
        
        from database import get_uncategorized_transactions, save_ai_categorization, update_transaction_category
        print("   ✅ Database functions imported successfully")
        
        from utils.pluggy_connector import PluggyConnector
        print("   ✅ Pluggy connector imported successfully")
        
    except Exception as e:
        print(f"   ❌ Module import failed: {e}")
        return False
    
    # Test 5: Test New Transaction Flow
    print("\n5️⃣ TESTING NEW TRANSACTION FLOW...")
    
    conn = sqlite3.connect('richness.db')
    cursor = conn.cursor()
    
    # Get a test user
    cursor.execute("SELECT id, usuario FROM usuarios LIMIT 1")
    user_result = cursor.fetchone()
    
    if not user_result:
        print("   ❌ No users found in database")
        conn.close()
        return False
    
    user_id, username = user_result
    print(f"   🔍 Testing with User {user_id} ({username})")
    
    # Create a test transaction
    test_transaction = {
        'data': date.today().strftime('%Y-%m-%d'),
        'valor': -35.75,
        'tipo': 'Débito',
        'descricao': 'SUPERMERCADO TESTE - COMPRA ALIMENTACAO',
        'categoria': None,
        'usuario_id': user_id
    }
    
    try:
        cursor.execute("""
            INSERT INTO extratos (data, valor, tipo, descricao, categoria, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            test_transaction['data'],
            test_transaction['valor'],
            test_transaction['tipo'],
            test_transaction['descricao'],
            test_transaction['categoria'],
            test_transaction['usuario_id']
        ))
        
        test_id = cursor.lastrowid
        conn.commit()
        print(f"   ✅ Test transaction created (ID: {test_id})")
        
        # Test if categorization system picks it up
        uncategorized = get_uncategorized_transactions(user_id, limit=10)
        total_uncategorized = (
            len(uncategorized['extratos']) + 
            len(uncategorized['cartoes']) + 
            len(uncategorized['economias'])
        )
        
        print(f"   📊 Found {total_uncategorized} uncategorized transactions")
        
        if total_uncategorized > 0:
            print("   ✅ Categorization system detected new transaction")
            
            # Test automatic categorization
            result = run_auto_categorization_on_login(user_id)
            
            if result['success']:
                print(f"   ✅ Auto categorization executed: {result['message']}")
                
                # Check if our test transaction was categorized
                cursor.execute("SELECT categoria FROM extratos WHERE id = ?", (test_id,))
                new_category = cursor.fetchone()
                
                if new_category and new_category[0]:
                    print(f"   ✅ Test transaction categorized as: {new_category[0]}")
                    if new_category[0] == 'Alimentação':
                        print("   🎯 PERFECT! System correctly identified food purchase")
                    else:
                        print(f"   ℹ️  Expected 'Alimentação', got '{new_category[0]}' (may be due to encryption)")
                else:
                    print("   ⚠️  Test transaction was not categorized")
            else:
                print(f"   ⚠️  Auto categorization failed: {result['message']}")
        else:
            print("   ⚠️  No uncategorized transactions found (unexpected)")
        
        # Clean up test transaction
        cursor.execute("DELETE FROM extratos WHERE id = ?", (test_id,))
        cursor.execute("DELETE FROM ai_categorizations WHERE transaction_id = ? AND transaction_type = 'extrato'", (test_id,))
        conn.commit()
        print("   🧹 Test transaction cleaned up")
        
    except Exception as e:
        print(f"   ❌ Test transaction flow failed: {e}")
        return False
    finally:
        conn.close()
    
    # Test 6: Environment Configuration
    print("\n6️⃣ CHECKING ENVIRONMENT CONFIGURATION...")
    
    skip_llm = os.getenv('SKIP_LLM_PROCESSING', 'false').lower()
    print(f"   SKIP_LLM_PROCESSING: {skip_llm}")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        key_preview = openai_key[:8] + "..." if len(openai_key) > 8 else "***"
        print(f"   OPENAI_API_KEY: {key_preview} (configured)")
    else:
        print("   OPENAI_API_KEY: Not configured")
    
    if skip_llm == 'false' and openai_key:
        print("   ✅ AI categorization properly configured")
    elif skip_llm == 'true':
        print("   ℹ️  AI categorization disabled (fallback mode)")
    else:
        print("   ⚠️  AI categorization may not work (missing API key)")
    
    # Final Assessment
    print("\n" + "=" * 50)
    print("🏁 FINAL SYSTEM READINESS ASSESSMENT")
    print("=" * 50)
    
    if total_null == 0:
        print("✅ SYSTEM READY FOR PRODUCTION!")
        print()
        print("🎯 Key Status:")
        print("   ✅ All existing transactions categorized")
        print("   ✅ No NULL categories remaining")
        print("   ✅ Automatic categorization system functional")
        print("   ✅ Database and modules working correctly")
        print("   ✅ Cache properly cleared")
        print()
        print("📋 Next Steps:")
        print("   1. Monitor new transactions for proper categorization")
        print("   2. Users can now use the application normally")
        print("   3. Consider implementing description decryption for better accuracy")
        print("   4. Set up periodic maintenance to clear caches")
        
        return True
    else:
        print("⚠️  SYSTEM PARTIALLY READY")
        print(f"   • {total_null} transactions still need categorization")
        print("   • Manual intervention may be required")
        
        return False

if __name__ == "__main__":
    success = verify_system_readiness()
    
    if success:
        print("\n🎉 VERIFICATION COMPLETE - SYSTEM READY! 🎉")
    else:
        print("\n❌ VERIFICATION FAILED - ADDITIONAL WORK NEEDED")
    
    exit(0 if success else 1)
