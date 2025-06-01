#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para analisar tipos de conta e transações para filtrar cartões de crédito
"""

from utils.pluggy_connector import PluggyConnector
from database import get_connection
import pandas as pd
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def get_usuario_id(usuario):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    row = cur.fetchone()
    return row[0] if row else None

def load_items_db(usuario):
    usuario_id = get_usuario_id(usuario)
    if usuario_id is None:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT item_id, nome FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
    return [{'item_id': row['item_id'], 'nome': row['nome']} for row in cur.fetchall()]

def main():
    print("=== ANÁLISE DE DADOS PARA CARTÕES DE CRÉDITO ===")
    
    # Conectar ao Pluggy
    try:
        pluggy = PluggyConnector()
        print("✅ Conectado ao Pluggy com sucesso")
    except Exception as e:
        print(f"❌ Erro ao conectar ao Pluggy: {e}")
        return

    # Buscar item IDs do banco
    usuario = 'arthur.cabral.r@gmail.com'
    items = load_items_db(usuario)
    print(f"📋 Items encontrados: {len(items)}")
    
    if not items:
        print("❌ Nenhum item encontrado para o usuário")
        return

    # Listar os items
    for i, item in enumerate(items):
        print(f"  {i+1}. {item['nome']} (ID: {item['item_id']})")

    # Buscar informações das contas primeiro
    print("\n=== INFORMAÇÕES DAS CONTAS ===")
    try:
        saldo_info = pluggy.obter_saldo_atual(items)
        if saldo_info and len(saldo_info) > 2:
            contas_detalhes = saldo_info[2]
            print(f"Total de contas: {len(contas_detalhes)}")
            
            contas_credito = []
            for conta in contas_detalhes:
                print(f"Conta: {conta['Nome da Conta']} | Tipo: {conta['Tipo']} | Item: {conta['Item']}")
                if conta['Tipo'] == 'CREDIT':
                    contas_credito.append(conta)
            
            print(f"\n🔍 Contas de crédito encontradas: {len(contas_credito)}")
            for conta in contas_credito:
                print(f"  - {conta['Nome da Conta']} ({conta['Item']})")
                
    except Exception as e:
        print(f"❌ Erro ao obter informações das contas: {e}")

    # Buscar transações para análise
    print("\n=== ANÁLISE DE TRANSAÇÕES ===")
    try:
        # Usar apenas 1 item para análise rápida
        df = pluggy.buscar_extratos(items[:1], dias=30)
        
        if not df.empty:
            print(f"📊 Total de transações encontradas: {len(df)}")
            print(f"📋 Colunas disponíveis: {list(df.columns)}")
            
            # Verificar tipos únicos
            if 'Tipo' in df.columns:
                tipos_unicos = df['Tipo'].unique()
                print(f"\n🏷️ Tipos de transação únicos: {tipos_unicos}")
                
                # Contar por tipo
                print(f"\n📈 Contagem por tipo:")
                print(df['Tipo'].value_counts().to_string())
            
            # Verificar contas
            if 'Conta' in df.columns:
                contas_unicas = df['Conta'].unique()
                print(f"\n🏦 Contas únicas ({len(contas_unicas)}):")
                for conta in contas_unicas:
                    print(f"  - {conta}")
                    
            # Mostrar algumas transações de exemplo
            print(f"\n📝 Exemplo de transações (primeiras 5):")
            colunas_importantes = ['Data', 'Valor', 'Descrição', 'Tipo', 'Conta']
            colunas_disponiveis = [col for col in colunas_importantes if col in df.columns]
            print(df[colunas_disponiveis].head().to_string())
            
        else:
            print("❌ Nenhuma transação encontrada")
            
    except Exception as e:
        print(f"❌ Erro ao buscar transações: {e}")

    print("\n=== ANÁLISE CONCLUÍDA ===")

if __name__ == "__main__":
    main()
