<script src="Js/Andamento_processo.js?v=<?php echo time(); ?>"></script>

<!-- Search Section -->
<div class="search-section">
    <div class="search-card">
        <div class="search-header">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
            </svg>
            <h2>Pesquisar Processo</h2>
        </div>
        
        <div class="search-body">
            <p class="search-description">Digite o RA, nome, número do processo ou andamento para localizar</p>
            
            <div class="search-input-group">
                <input 
                    type="text" 
                    id="txt_pesquisa_processo" 
                    name="txt_pesquisa_processo" 
                    class="search-input" 
                    placeholder="Digite sua pesquisa..."
                    autocomplete="off"
                >
                <button 
                    id="btn_pesquisar_processo" 
                    class="search-button" 
                    onclick="Carregar_Grid_processos();"
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.35-4.35"></path>
                    </svg>
                    <span>Pesquisar</span>
                </button>
            </div>
        </div>
    </div>
    
    <!-- Results Grid -->
    <div class="results-container">
        <div id="div_grid_localizar_proc"></div>
        <div id="div_grid_localizar_proc_example"></div>
    </div>
</div>

<div class="divider"></div>

<!-- Process Details Section -->
<div id="div_processo" class="process-details" style="display:none;">
    
    <!-- Defendant Information -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <h3>Réu</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row">
                <div class="form-group" style="flex: 0 0 100px;">
                    <label class="form-label">Código</label>
                    <input id="txt_cod_reu" class="form-control" readonly />
                </div>
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Nome</label>
                    <input id="txt_nome_reu" class="form-control" readonly />
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Andamento</label>
                    <input id="txt_cod_andamento" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Data de Cadastro</label>
                    <input id="txt_dt_cadastro" class="form-control" readonly />
                </div>
            </div>
        </div>
    </div>

    <!-- Lawyer Information -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="9" y1="9" x2="15" y2="9"></line>
                <line x1="9" y1="15" x2="15" y2="15"></line>
            </svg>
            <h3>Advogado</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row">
                <div class="form-group" style="flex: 0 0 100px;">
                    <label class="form-label">Código</label>
                    <input id="txt_cod_advogado" class="form-control" readonly />
                </div>
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Nome</label>
                    <input id="txt_nome_advogado" class="form-control" readonly />
                </div>
            </div>
        </div>
    </div>

    <!-- Action Information -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            <h3>Ação</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row">
                <div class="form-group" style="flex: 0 0 100px;">
                    <label class="form-label">Código</label>
                    <input id="txt_cod_acao" class="form-control" readonly />
                </div>
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Ação</label>
                    <input id="txt_nome_acao" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Data Distribuição</label>
                    <input id="txt_data_dist" class="form-control" readonly />
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Vara</label>
                    <input id="txt_vara" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Nº Processo</label>
                    <input id="txt_n_processo" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Apenso 1</label>
                    <input id="txt_apenso_1" class="form-control" readonly />
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group" style="flex: 0 0 100px;">
                    <label class="form-label">Código Autor</label>
                    <input id="txt_cod_autor" class="form-control" readonly />
                </div>
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Nome Autor</label>
                    <input id="txt_nome_autor" class="form-control" readonly />
                </div>
            </div>
        </div>
    </div>

    <!-- Debts Information -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="1" x2="12" y2="23"></line>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
            <h3>Débitos</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Débito Ano</label>
                    <input id="txt_deb_ano" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Mês/Ano Inicial</label>
                    <input id="txt_mes_ini" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Mês/Ano Final</label>
                    <input id="txt_mes_fim" class="form-control" readonly />
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Valor Descumprido</label>
                    <input id="txt_valor_desc" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Total Dívida</label>
                    <input id="txt_total_divida" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Acordo Celebrado</label>
                    <input id="txt_acordo" class="form-control" readonly />
                </div>
                <div class="form-group">
                    <label class="form-label">Despesas Processuais</label>
                    <input id="txt_despesas" class="form-control" readonly />
                </div>
            </div>
        </div>
    </div>

    <!-- Debt Records -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 5H2v7h7V5Z"></path>
                <path d="M22 5h-7v7h7V5Z"></path>
                <path d="M9 17H2v7h7v-7Z"></path>
                <path d="M22 17h-7v7h7v-7Z"></path>
            </svg>
            <h3>Ficha de Débitos</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row" style="align-items: flex-end;">
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Nº Ficha</label>
                    <input id="txt_ficha" class="form-control" />
                </div>
                <button 
                    id="btn_inclui_ficha" 
                    class="action-button" 
                    onclick="fnc_incluir_ficha();"
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    <span>Incluir Ficha</span>
                </button>
            </div>
            
            <div class="grid-container">
                <div id="div_grid_ficha_debito"></div>
                <div id="div_grid_ficha_debito_example"></div>
            </div>
        </div>
    </div>

    <!-- Reports Section -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <h3>Relatórios</h3>
        </div>
        
        <div class="card-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Data</label>
                    <input id="txt_data_rel" class="form-control" />
                </div>
                <div class="form-group" style="flex: 1;">
                    <label class="form-label">Estagiário(a)</label>
                    <input id="txt_estagiario" class="form-control" />
                </div>
            </div>
            
            <div class="reports-grid">
                <button class="report-button" onclick="fnc_imprimir_rel_procuracao();">
                    Procuração
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_monitoria_I();">
                    Monitória 1
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_monitoria_II();">
                    Monitória 2
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_monitoria_III();">
                    Monitória 3
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_monitoria_IV();">
                    Monitória 4
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_monitoria_V();">
                    Monitória 5
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_peticao_exec();">
                    Petição de Execução
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_peticao_exec_II();">
                    Petição de Execução 2
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_ficha_andamento();">
                    Ficha de Andamento
                </button>
                <button class="report-button" onclick="fnc_imprimir_rel_ficha_andamento_ativ();">
                    Ficha And./Atividade
                </button>
                <button class="report-button" onclick="modal_parametros('s1');">
                    Petição Suspensão I
                </button>
                <button class="report-button" onclick="modal_parametros('s2');">
                    Petição Suspensão II
                </button>
                <button class="report-button" onclick="modal_parametros('e1');">
                    Extinção I
                </button>
                <button class="report-button" onclick="modal_parametros('e2');">
                    Extinção II
                </button>
            </div>
        </div>
    </div>

    <!-- Document Generation -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="12" y1="18" x2="12" y2="12"></line>
                <line x1="9" y1="15" x2="15" y2="15"></line>
            </svg>
            <h3>Geração de Documentos Processuais</h3>
        </div>
        
        <div class="card-body">
            <!-- Container de Seleções Dinâmicas -->
            <div id="dynamic-selections-container">
                <!-- Os conjuntos de inputs serão adicionados aqui dinamicamente -->
            </div>

            <!-- Botão para adicionar nova seleção -->
            <button class="action-button secondary" onclick="adicionarNovaSelecao()" style="margin-top: var(--spacing-md);">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>Adicionar Nova Seleção</span>
            </button>

            <!-- Preview do Texto Base -->
            <div id="texto-preview-container" style="display: none; margin-top: var(--spacing-xl);">
                <h4 class="subsection-title">Preview do Texto Base</h4>
                <div id="texto-preview-content" class="preview-box"></div>
            </div>

            <!-- Botões de Ação -->
            <div class="action-buttons-group" style="margin-top: var(--spacing-xl); display: flex; gap: var(--spacing-md); flex-wrap: wrap;">
                <button class="action-button primary" onclick="geraDocWordNovo()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span>Gerar Documento</span>
                </button>
                
                
                <button class="action-button secondary" onclick="limparSelecoes()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                    <span>Limpar Tudo</span>
                </button>
            </div>

            <div class="document-models" style="margin-top: var(--spacing-2xl);">
                <h4 class="subsection-title">Gerenciar Modelos de Documentos</h4>
                <button class="action-button secondary" onclick="adicionarImagem()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                    <span>Anexar Novo Documento Base</span>
                </button>
                <div id="gridDocsModelo" style="margin-top: var(--spacing-md);"></div>
            </div>
        </div>
    </div>

    <!-- Students Section -->
    <div class="info-card">
        <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <h3>Alunos</h3>
        </div>
        
        <div class="card-body">
            <div class="student-list">
                <input id="txt_aluno1" class="student-input" placeholder="Aluno 1" />
                <input id="txt_aluno2" class="student-input" placeholder="Aluno 2" />
                <input id="txt_aluno3" class="student-input" placeholder="Aluno 3" />
            </div>
        </div>
    </div>
</div>

<!-- Modal Containers -->
<div id="divWindow" hidden></div>
<div id="windowGeraDoc" hidden></div>
<div id="windowNovaSolicitacao" hidden></div>
<div id="WINDOW_EDITA_GRUPO" hidden></div>
<div id="tipo_relat" hidden></div>
<div id="modal_parametro" hidden></div>

<!-- Forms -->
<form action="http://192.168.255.14/Relatorios_Crystal/Crystal_relat_web.php" target="_blank" method="post" id="formIndex"></form>
<form action="http://192.168.255.14/Relatorios_Crystal/Crystal_relat_web_ext_I_II.php" target="_blank" method="post" id="formIndex2"></form>

<style>
/* Additional Styles for Andamento Page */
.search-section {
    margin-bottom: var(--spacing-2xl);
}

.search-card {
    background: var(--color-surface);
    border-radius: var(--radius-xl);
    padding: var(--spacing-xl);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
}

.search-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
}

.search-icon {
    width: 28px;
    height: 28px;
    color: var(--color-accent);
}

.search-header h2 {
    font-family: var(--font-display);
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary);
    margin: 0;
}

.search-description {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
}

.search-input-group {
    display: flex;
    gap: var(--spacing-md);
}

.search-input {
    flex: 1;
    font-size: var(--font-size-lg);
    padding: var(--spacing-lg);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    transition: all var(--transition-base);
}

.search-input:focus {
    border-color: var(--color-accent);
    box-shadow: 0 0 0 4px rgba(212, 175, 55, 0.1);
}

.search-button {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-lg) var(--spacing-2xl);
    background: linear-gradient(135deg, var(--color-accent-dark), var(--color-accent));
    color: var(--color-primary);
    border: none;
    border-radius: var(--radius-lg);
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    transition: all var(--transition-base);
    box-shadow: var(--shadow-md);
}

.search-button:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

.search-button svg {
    width: 20px;
    height: 20px;
}

.results-container {
    margin-top: var(--spacing-xl);
}

.divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--color-border), transparent);
    margin: var(--spacing-2xl) 0;
}

.process-details {
    animation: slideIn 400ms var(--transition-base);
}

/* Estilos para Seleções Dinâmicas */
.selection-group {
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    position: relative;
    transition: all var(--transition-base);
}

.selection-group:hover {
    border-color: var(--color-accent);
    box-shadow: var(--shadow-sm);
}

.selection-group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
    padding-bottom: var(--spacing-sm);
    border-bottom: 2px solid var(--color-border-light);
}

.selection-group-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary);
}

.btn-remove-selection {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: #dc3545;
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: all var(--transition-base);
}

.btn-remove-selection:hover {
    background: #c82333;
    transform: translateY(-1px);
}

.btn-remove-selection svg {
    width: 16px;
    height: 16px;
}

.selection-inputs {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--spacing-md);
}

.preview-box {
    background: white;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    max-height: 400px;
    overflow-y: auto;
    font-family: 'Georgia', serif;
    line-height: 1.6;
}

.preview-box:empty::before {
    content: "Selecione uma subcategoria para visualizar o texto base...";
    color: var(--color-text-muted);
    font-style: italic;
}

.action-buttons-group {
    padding-top: var(--spacing-lg);
    border-top: 2px solid var(--color-border-light);
}

/* Estilos para os dropdowns do Kendo */
.k-dropdown {
    width: 100% !important;
}

@media (max-width: 768px) {
    .selection-inputs {
        grid-template-columns: 1fr;
    }
    
    .action-buttons-group {
        flex-direction: column;
    }
}

.info-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-border);
    margin-bottom: var(--spacing-xl);
    overflow: hidden;
}

.card-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-lg) var(--spacing-xl);
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
    border-bottom: 3px solid var(--color-accent);
}

.card-icon {
    width: 24px;
    height: 24px;
    color: var(--color-accent);
}

.card-header h3 {
    font-family: var(--font-display);
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-surface);
    margin: 0;
}

.card-body {
    padding: var(--spacing-xl);
}

.form-row {
    display: flex;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    flex-wrap: wrap;
}

.form-row:last-child {
    margin-bottom: 0;
}

.form-group {
    flex: 1;
    min-width: 200px;
}

.form-label {
    display: block;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--spacing-sm);
}

.form-control {
    width: 100%;
    padding: var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    transition: all var(--transition-fast);
}

.form-control:focus {
    outline: none;
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.1);
}

.form-control[readonly] {
    background: var(--color-bg-secondary);
    color: var(--color-text-muted);
}

.action-button {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-xl);
    background: linear-gradient(135deg, var(--color-accent-dark), var(--color-accent));
    color: var(--color-primary);
    border: none;
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: all var(--transition-base);
    box-shadow: var(--shadow-sm);
}

.action-button:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.action-button svg {
    width: 18px;
    height: 18px;
}

.action-button.secondary {
    background: var(--color-secondary);
    color: var(--color-surface);
}

.action-button.primary {
    padding: var(--spacing-lg) var(--spacing-xl);
    font-size: var(--font-size-lg);
}

.reports-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
}

.report-button {
    padding: var(--spacing-lg);
    background: var(--color-surface);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    color: var(--color-primary);
    cursor: pointer;
    transition: all var(--transition-base);
}

.report-button:hover {
    border-color: var(--color-accent);
    background: var(--color-accent-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}

.subsection-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary);
    margin: var(--spacing-xl) 0 var(--spacing-md);
}

.document-models {
    margin-top: var(--spacing-xl);
    padding-top: var(--spacing-xl);
    border-top: 2px solid var(--color-border-light);
}

.student-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
}

.student-input {
    padding: var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    transition: all var(--transition-fast);
}

.student-input:focus {
    outline: none;
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.1);
}

.grid-container {
    display: flex;
    gap: var(--spacing-lg);
    margin-top: var(--spacing-lg);
    flex-wrap: wrap;
}

@media (max-width: 768px) {
    .search-input-group {
        flex-direction: column;
    }
    
    .reports-grid {
        grid-template-columns: 1fr;
    }
    
    .form-row {
        flex-direction: column;
    }
    
    .form-group {
        min-width: 100%;
    }
}
</style>
