<?php session_start(); ?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="ROBOTS" content="NOINDEX, NOFOLLOW">    
    <meta http-equiv="cache-control" content="no-cache">
    <meta http-equiv="pragma" content="no-cache">
    <meta http-equiv="expires" content="-1"> 
    
    <title>Sistema Jurídico Anchieta</title>
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="Imagens/law.png">
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
    
    <!-- Styles -->
    <link rel="stylesheet" href="Css/sistema-moderno.css?v=<?php echo time();?>" />
    <link rel="stylesheet" href="../telerik/styles/kendo.common-bootstrap.min.css" />
    <link rel="stylesheet" href="../telerik/styles/kendo.bootstrap.min.css" /> 

    <!-- Scripts -->
    <script src="../telerik/js/jquery.min.js"></script>
    <script src="../telerik/js/kendo.all.min.js"></script>
    <script src="../telerik/js/jszip.min.js"></script>
    <script src="../telerik/wrappers/php/content/js/cultures/kendo.culture.pt-BR.min.js"></script>
    <script src="Js/Index.js?v=<?php echo time();?>" ></script>
</head>    
<body>

    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner"></div>
    </div>
    
    <!-- Pop Container -->
    <div class='pop-container' id='pop_container'></div>   
    
    <!-- Hidden Input -->
    <input type="hidden" id="txt_usuario" name="txt_usuario" value="<?php echo $_REQUEST["usuario"]; ?>">

    <!-- Main Container -->
    <main class="main-container">
        <!-- Header Section -->
        <header class="page-header">
            <div class="header-content">
                <div class="header-title">
                    <h1>Sistema de Gestão Jurídica</h1>
                    <p class="header-subtitle">Gerenciamento integrado de processos e documentação</p>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="nav-tabs-container">
            <div class="nav-tabs" id="mainNavTabs">
                <button class="nav-tab active" data-target="exporta-pessoa">
                    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                    <span>Exportar Pessoa</span>
                </button>
                
                <button class="nav-tab" data-target="andamento">
                    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    <span>Andamento do Processo</span>
                </button>
            </div>
        </nav>

        <!-- Content Panels -->
        <div class="content-panels">
            <!-- Panel: Exportar Pessoa -->
            <section class="content-panel active" id="panel-exporta-pessoa">
                <div class="panel-content">
                    <div id="div_exporta_pessoa"></div>
                </div>
            </section>

            <!-- Panel: Andamento -->
            <section class="content-panel" id="panel-andamento">
                <div class="panel-content">
                    <div id="div_andamento"></div>
                </div>
            </section>
        </div>
    </main>
    
    <script>
        // Modern Tab Navigation
        document.addEventListener('DOMContentLoaded', function() {
            const tabs = document.querySelectorAll('.nav-tab');
            const panels = document.querySelectorAll('.content-panel');
            
            tabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    const target = this.dataset.target;
                    
                    // Update active tab
                    tabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Update active panel
                    panels.forEach(p => p.classList.remove('active'));
                    document.getElementById(`panel-${target}`).classList.add('active');
                    
                    // Load content
                    loadContent(target);
                });
            });
            
            // Load initial content
            loadContent('exporta-pessoa');
        });
        
        function loadContent(target) {
            //const loadingOverlay = document.getElementById('loadingOverlay');
            //loadingOverlay.classList.add('active');
            
            if (target === 'exporta-pessoa') {
                $("#div_exporta_pessoa").load("Php/Exporta_pessoa_modernizado.php", function() {
                    //loadingOverlay.classList.remove('active');
                });
            } else if (target === 'andamento') {
                $("#div_andamento").load("Php/Andamento_processo_modernizado.php", function() {
                    //loadingOverlay.classList.remove('active');
                });
            }
        }
        
        // Modern Alert Function
        window.kendoAlert = function(msg) {
            var win = $("<div>").kendoWindow({
                modal: true, 
                title: "Atenção",
                actions: ["Close"],
                animation: {
                    open: { effects: "fadeIn zoom:in", duration: 300 },
                    close: { effects: "fadeOut zoom:out", duration: 300 }
                },
                width: 400,
                position: { top: "50%", left: "50%" }
            }).getKendoWindow();

            win.content(msg);
            win.center().open();
        };

        function fnc_mensagem_resposta(e) {
            kendoAlert(e);
            $("#div_cadastro").data("kendoGrid").dataSource.read();
        }
    </script>       
  
</body>
</html>
