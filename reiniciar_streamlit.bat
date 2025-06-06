@echo off
echo ===========================================================
echo REINICIADOR E CORRETOR DO LANGCHAIN PARA RICHNESS
echo ===========================================================

echo Parando processos Streamlit existentes...
taskkill /f /im streamlit.exe >nul 2>&1

echo.
echo Desinstalando versoes atuais do LangChain...
pip uninstall -y langchain langchain-core langchain-community langchain-openai langchain-text-splitters langsmith regex tiktoken

echo.
echo Instalando versoes compativeis...
pip install regex==2023.12.25
pip install langchain==0.0.350
pip install langchain-openai==0.0.5

echo.
echo Verificando e corrigindo chave API...
python verificar_api_key.py

echo.
echo Corrigindo arquivo principal...
python corrigir_arquivo_dicas.py

echo.
echo Iniciando a aplicacao Streamlit...
streamlit run Home.py

echo.
echo Aplicacao reiniciada!
