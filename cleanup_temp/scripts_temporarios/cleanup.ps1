# Script PowerShell para limpeza do projeto
Write-Host "🧹 LIMPEZA DO PROJETO RICHNESS" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Criar estrutura de pastas se não existir
$folders = @(
    "cleanup_temp\tests",
    "cleanup_temp\docs_antigos", 
    "cleanup_temp\scripts_temporarios",
    "cleanup_temp\relatorios"
)

foreach ($folder in $folders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Host "✅ Pasta criada: $folder" -ForegroundColor Green
    }
}

# Arquivos de teste para mover
$testFiles = @(
    "health_check.py",
    "quick_check.py", 
    "simple_auto_cat_test.py",
    "simple_fix.py",
    "verify_changes.py",
    "verify_system_ready.py"
)

# Scripts temporários para mover
$scriptFiles = @(
    "categorization_fix_summary.py",
    "cleanup_final.py", 
    "execute_fix.py",
    "final_status_report.py",
    "final_system_verification.py",
    "fix_categorization.py",
    "fix_categorization_corrected.py",
    "fix_user4_categorization.py",
    "run_fix.py",
    "inspect_database.py",
    "verificacao_final_sistema.py",
    "verificacao_sistema_restaurado.py"
)

# Relatórios para mover
$reportFiles = @(
    "CATEGORIZATION_FIX_DOCUMENTATION.md",
    "CHECKLIST_VERIFICACAO_FINAL.md",
    "CORRECAO_IA_RELATORIO_FINAL.md",
    "GUIA_TESTE_SISTEMA_RESTAURADO.md", 
    "IMPLEMENTACAO_FINAL_CATEGORIZAÇÃO.md",
    "RELATORIO_MELHORIAS_CATEGORIZACAO.md",
    "RELATORIO_OTIMIZACAO_GRAFICOS.md",
    "SISTEMA_CATEGORIZAÇÃO_STATUS_FINAL.md",
    "STATUS_FINAL_SISTEMA.md"
)

# Mover arquivos de teste
Write-Host "`n🧪 Movendo arquivos de teste..." -ForegroundColor Yellow
$movedTests = 0
foreach ($file in $testFiles) {
    if (Test-Path $file) {
        Move-Item $file "cleanup_temp\tests\" -Force
        Write-Host "  📁 $file → cleanup_temp\tests\" -ForegroundColor Cyan
        $movedTests++
    }
}

# Mover scripts temporários
Write-Host "`n🔧 Movendo scripts temporários..." -ForegroundColor Yellow
$movedScripts = 0
foreach ($file in $scriptFiles) {
    if (Test-Path $file) {
        Move-Item $file "cleanup_temp\scripts_temporarios\" -Force
        Write-Host "  📁 $file → cleanup_temp\scripts_temporarios\" -ForegroundColor Cyan
        $movedScripts++
    }
}

# Mover relatórios
Write-Host "`n📄 Movendo relatórios..." -ForegroundColor Yellow
$movedReports = 0
foreach ($file in $reportFiles) {
    if (Test-Path $file) {
        Move-Item $file "cleanup_temp\relatorios\" -Force
        Write-Host "  📁 $file → cleanup_temp\relatorios\" -ForegroundColor Cyan
        $movedReports++
    }
}

# Remover __pycache__
Write-Host "`n🗑️ Removendo caches..." -ForegroundColor Yellow
$removedCache = 0
Get-ChildItem -Path . -Recurse -Name "__pycache__" -Directory | ForEach-Object {
    Remove-Item $_ -Recurse -Force
    Write-Host "  🗑️ Cache removido: $_" -ForegroundColor Red
    $removedCache++
}

# Resumo final
Write-Host "`n🎉 LIMPEZA CONCLUÍDA!" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "📊 Resumo:" -ForegroundColor White
Write-Host "  📁 Testes movidos: $movedTests" -ForegroundColor Cyan
Write-Host "  🔧 Scripts movidos: $movedScripts" -ForegroundColor Cyan  
Write-Host "  📄 Relatórios movidos: $movedReports" -ForegroundColor Cyan
Write-Host "  🗑️ Caches removidos: $removedCache" -ForegroundColor Red

Write-Host "`n✅ Estrutura limpa e organizada!" -ForegroundColor Green
