var v_RA1, v_RA2, v_RA3;

// ============================================
// VARIÁVEIS GLOBAIS PARA NOVA FUNCIONALIDADE
// ============================================
let selectionCounter = 0;
let selectionsData = [];

// ============================================
// MAPA DE INPUTS PARA JSON
// ============================================
const inputFieldsMap = {
  reu: {
    codigoReu: "txt_cod_reu",
    nomeReu: "txt_nome_reu",
    codigoAndamento: "txt_cod_andamento",
    dataCadastro: "txt_dt_cadastro"
  },
  advogado: {
    codigoAdvogado: "txt_cod_advogado",
    nomeAdvogado: "txt_nome_advogado"
  },
  acao: {
    codigoAcao: "txt_cod_acao",
    nomeAcao: "txt_nome_acao",
    dataDistribuicao: "txt_data_dist",
    vara: "txt_vara",
    numeroProcesso: "txt_n_processo",
    apenso1: "txt_apenso_1",
    codigoAutor: "txt_cod_autor",
    nomeAutor: "txt_nome_autor"
  },
  debitos: {
    debitoAno: "txt_deb_ano",
    mesAnoInicial: "txt_mes_ini",
    mesAnoFinal: "txt_mes_fim",
    valorDescumprido: "txt_valor_desc",
    totalDivida: "txt_total_divida",
    acordoCelebrado: "txt_acordo",
    despesasProcessuais: "txt_despesas"
  }
};

/**
 * Extrai os dados dos inputs conforme o mapa de campos
 * @returns {Object} Objeto estruturado com todos os dados
 */
function extrairDadosFormulario() {
  const dados = {};
  
  // Iterar por cada seção
  for (const secao in inputFieldsMap) {
    dados[secao] = {};
    
    // Iterar por cada campo na seção
    for (const campo in inputFieldsMap[secao]) {
      const elementId = inputFieldsMap[secao][campo];
      const valor = $(`#${elementId}`).val();
      dados[secao][campo] = valor || null;
    }
  }
  
  return dados;
}

/**
 * Função auxiliar para obter um campo específico
 * @param {string} secao - Nome da seção (ex: 'reu', 'advogado')
 * @param {string} campo - Nome do campo (ex: 'codigoReu')
 * @returns {string} Valor do campo
 */
function obterCampo(secao, campo) {
  if (inputFieldsMap[secao] && inputFieldsMap[secao][campo]) {
    const elementId = inputFieldsMap[secao][campo];
    return $(`#${elementId}`).val();
  }
  return null;
}

$(document).ready(function () {
  $("#pop_container").load("Php/popup_modernizado.php");
  $("#modal_parametro").hide();

  /*$("#txt_data_rel").kendoDatePicker({
			culture:"pt-BR",
		}); */
  var el = document.getElementById("contentAppend");
  if (el) {
    el.addEventListener("click", function (e) {
      regarregaComboPorTarget(e.target.id);
    });
  }
});

//FUNÇÃO PARA LIMPAR O GRID
function fnc_limpar_grid_processo() {
  if (!$("#div_grid_localizar_proc").length) {
    $("#div_grid_localizar_proc_example").append(
      "<div id='div_grid_localizar_proc' ></div>"
    );
  } else {
    $("#div_grid_localizar_proc").remove();
    $("#div_grid_localizar_proc_example").append(
      "<div id='div_grid_localizar_proc' ></div>"
    );
  }
}



function Carregar_Grid_processos() {
  $("#div_processo").hide();
  fnc_limpar_campos();
  fnc_limpar_grid_processo();
  let v_codigo = $("#txt_pesquisa_processo").val();
  
  // Estado de loading
  const $btnPesquisar = $("#btn_pesquisar_processo");
  $btnPesquisar.addClass('loading').prop('disabled', true);

  CarregarGrid_processo = new kendo.data.DataSource({
    batch: true,
    transport: {
      read: {
        url: "Banco/Carregar_grid_processos.php",
        data: {
          CODIGO: v_codigo,
        },
        cache: false,
      },
      error: function(e) {
        console.error('Erro ao carregar dados:', e);
        $btnPesquisar.removeClass('loading').prop('disabled', false);
      },
      cache: false,
    },
    batch: false,
    schema: {
      data: "data_grid_processos",
      model: {
        id: "ID_PROCESSO",
        fields: {
          ID_PROCESSO: { nullable: false, editable: true },
          TITPROC: { nullable: false, editable: true },
          ALTERAVEL1: { nullable: false, editable: true },
          NOME: { nullable: false, editable: true },
          CNPJ: { nullable: false, editable: true },
          NOME_ALUNO: { nullable: false, editable: true },
        },
      },
    },
  });

  $("#div_grid_localizar_proc").kendoGrid({
    dataSource: CarregarGrid_processo,
    scrollable: false,
    dataBound: function() {
      $btnPesquisar.removeClass('loading').prop('disabled', false);
    },
    noRecords: {
      template:
        '<tr class="kendo-data-row"><td colspan="\' + colCount + \'" class="no-data">Nenhuma informação encontrada.</td></tr>',
    },
    columns: [
      {
        field: "ALTERAVEL1",
        title: "Aluno",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        field: "NOME_ALUNO",
        title: "Nome aluno",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        field: "NOME",
        title: "Nome resp.",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        field: "CNPJ",
        title: "CPF",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        field: "ID_PROCESSO",
        title: "Nº Processo",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        field: "TITPROC",
        title: "Processo",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        command: [
          {
            text: "Selecionar",
            name: "Selecionar_proc",
            click: fnc_localizar_processo,
          },
        ],
        title: "Escolher",
        headerAttributes: { style: "text-align:center; font-weight: bold;" },
        attributes: { style: "text-align:center;" },
      },
    ],
    batch: true,
    schema: {
      model: { id: "id" },
    },
  });
}

$("#txt_pesquisa_processo").keypress(function(e) {
    if (e.which == 13) {
        Carregar_Grid_processos();
    }
});

function fnc_localizar_processo(e) {
  Carregar_Grid_modelos();
  carregarModelo();
  $("#div_grid_localizar_proc").hide();
  $("#div_processo").show();
  v_processo = 0;
  e.preventDefault();
  var dataItem_proc = this.dataItem($(e.currentTarget).closest("tr"));

  v_processo = dataItem_proc.ID_PROCESSO;

  $.ajax({
    type: "POST",
    url: "Banco/Consultar_dados_processo.php",
    data: {
      PROCESSO: v_processo,
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      var v_ID_PROCESSO = json.ID_PROCESSO;
      var v_DATA_CADASTRO = json.DATA_CADASTRO;
      var v_COD_REU = json.COD_REU;
      var v_NOME_REU = json.NOME_REU;
      var v_COD_ADVOG = json.COD_ADVOG;
      var v_ADVOGADO = json.ADVOGADO;
      var v_ID_ACAO = json.ID_ACAO;
      var v_NM_ACAO = json.NM_ACAO;
      var v_DATA_DIST = json.DATA_DIST;
      var v_VARA = json.VARA;
      var v_NUMPROC = json.NUMPROC;
      var v_APENSO = json.APENSO;
      var v_COD_AUTOR = json.COD_AUTOR;
      var v_AUTOR = json.AUTOR;
      var v_MES_ANO_INI = json.MES_ANO_INI;
      var v_MES_ANO_FIM = json.MES_ANO_FIM;
      var v_DEBITO_ANO = json.DEBITO_ANO;
      var v_TOTAL_DA_DIVIDA = json.TOTAL_DA_DIVIDA;
      var v_VALOR_DESCUMPRIDO = json.VALOR_DESCUMPRIDO;
      var v_ACORDO_CELEBRADO = json.ACORDO_CELEBRADO;
      v_RA1 = json.RA1;
      v_RA2 = json.RA2;
      v_RA3 = json.RA3;
      var v_DESPESAS = json.DESPESAS_PROCESSUAIS;

      $("#txt_despesas").val(v_DESPESAS);
      $("#txt_cod_reu").val(v_COD_REU);
      $("#txt_nome_reu").val(v_NOME_REU);
      $("#txt_cod_advogado").val(v_COD_ADVOG);
      $("#txt_nome_advogado").val(v_ADVOGADO);
      $("#txt_cod_acao").val(v_ID_ACAO);
      $("#txt_nome_acao").val(v_NM_ACAO);
      $("#txt_data_dist").val(v_DATA_DIST);
      $("#txt_vara").val(v_VARA);
      $("#txt_n_processo").val(v_NUMPROC);
      $("#txt_apenso_1").val(v_APENSO);
      $("#txt_cod_autor").val(v_COD_AUTOR);
      $("#txt_nome_autor").val(v_AUTOR);
      $("#txt_deb_ano").val(v_DEBITO_ANO);
      $("#txt_mes_ini").val(v_MES_ANO_INI);
      $("#txt_mes_fim").val(v_MES_ANO_FIM);
      $("#txt_valor_desc").val(v_VALOR_DESCUMPRIDO);
      $("#txt_total_divida").val(v_TOTAL_DA_DIVIDA);
      $("#txt_acordo").val(v_ACORDO_CELEBRADO);
      $("#txt_cod_andamento").val(v_ID_PROCESSO);
      $("#txt_dt_cadastro").val(v_DATA_CADASTRO);

      // Popula lista dinâmica de alunos
      var alunosDoProcesso = [
        { nome: json.NOME_ALUNO1, ra: json.RA1 },
        { nome: json.NOME_ALUNO2, ra: json.RA2 },
        { nome: json.NOME_ALUNO3, ra: json.RA3 }
      ].filter(function(a) { return a.nome || a.ra; });
      carregarAlunosDinamicos(alunosDoProcesso);

      Carregar_Grid_ficha();
      carregar_cmb_estagiario();
      fnc_verificar_ra_processo(v_ID_PROCESSO, v_RA1, v_RA2, v_RA3);
      
      // Adicionar primeira seleção automaticamente
      setTimeout(function() {
        if ($('.selection-group').length === 0) {
          adicionarNovaSelecao();
        }
      }, 500);
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Atenção</b>",
          message: "Processo não encontrado!",
        },
        "info"
      );
    },
  });
}

//FUNÇÃO PARA LIMPAR O GRID
function fnc_limpar_grid_ficha() {
  if (!$("#div_grid_ficha_debito").length) {
    $("#div_grid_ficha_debito_example").append(
      "<div id='div_grid_ficha_debito' ></div>"
    );
  } else {
    $("#div_grid_ficha_debito").remove();
    $("#div_grid_ficha_debito_example").append(
      "<div id='div_grid_ficha_debito' ></div>"
    );
  }
}

function Carregar_Grid_ficha() {
  fnc_limpar_grid_ficha();
  var v_codigo = $("#txt_cod_andamento").val();

  CarregarGrid_ficha = new kendo.data.DataSource({
    batch: true,
    transport: {
      read: {
        url: "Banco/Carregar_grid_ficha.php",
        data: {
          CODIGO: v_codigo,
        },
        cache: false,
      },
      destroy: {
        async: false,
        url: "Banco/Excluir_ficha.php",
        cache: false,
        complete: function (e) {
          $("#div_grid_ficha_debito").data("kendoGrid").dataSource.read();
        },
      },
      cache: false,
    },
    batch: false,
    schema: {
      data: "data_grid_ficha",
      model: {
        id: "id_processo",
        fields: {
          id_processo: { nullable: false, editable: true },
          id_anchi_rel_ficha_debito: { nullable: false, editable: true },
        },
      },
    },
  });

  $("#div_grid_ficha_debito").kendoGrid({
    dataSource: CarregarGrid_ficha,
    scrollable: false,
    editable: {
      confirmation: "Deseja mesmo excluir?",
      mode: "popup",
    },
    noRecords: {
      template:
        '<tr class="kendo-data-row"><td colspan="\' + colCount + \'" class="no-data">Nenhuma informação encontrada.</td></tr>',
    },
    columns: [
      {
        field: "id_anchi_rel_ficha_debito",
        title: "Ficha",
        headerAttributes: { style: "text-align:center;  font-weight: bold;" },
        encoded: false,
        attributes: { style: "text-align:center;" },
      },
      {
        command: [{ name: "destroy", text: "Excluir" }],
        title: "Excluir",
        headerAttributes: { style: "text-align:center; font-weight: bold;" },
        attributes: { style: "text-align:center;" },
      },
    ],
    batch: true,
    schema: {
      model: { id: "id" },
    },
  });
}

function fnc_incluir_ficha() {
  var v_ficha = $("#txt_ficha").val();
  var v_processo = $("#txt_cod_andamento").val();

  $.ajax({
    type: "POST",
    url: "Banco/Inserir_ficha.php",
    data: {
      FICHA: v_ficha,
      PROCESSO: v_processo,
    },
    cache: false,
    dataType: "json",
    complete: function (json) {
      $("#div_grid_ficha_debito").data("kendoGrid").dataSource.read();
    },
  });
}

function carregar_cmb_estagiario() {
  Carregarcombo_estagiario = new kendo.data.DataSource({
    batch: true,
    transport: {
      read: {
        url: "Banco/Carregar_combo_estagiario.php",
        cache: false,
      },
    },
    batch: false,
    schema: {
      data: "data_cmb_estag",
      model: {
        id: "ID_PESSOA",
        fields: {
          ID_PESSOA: { nullable: true },
          NOME: { nullable: true },
        },
      },
    },
  });

  $("#txt_estagiario").kendoDropDownList({
    dataTextField: "NOME",
    dataValueField: "ID_PESSOA",
    dataSource: Carregarcombo_estagiario,
    filter: "contains",
    optionLabel: "Selecione...",
  });
}

function carregar_cmb_doc() {
  Carregarcombo_doc = new kendo.data.DataSource({
    batch: true,
    transport: {
      read: {
        url: "Banco/CarregarDocs.php",
        cache: false,
      },
    },
    batch: false,
    schema: {
      data: "data_cmb_estag",
      model: {
        id: "VALOR",
        fields: {
          VALOR: { nullable: true },
          TEXTO: { nullable: true },
        },
      },
    },
  });

  $("#txt_DOCS").kendoDropDownList({
    dataTextField: "TEXTO",
    dataValueField: "VALOR",
    dataSource: Carregarcombo_doc,
    filter: "contains",
    optionLabel: "Selecione...",
  });
}

function fnc_verificar_ra_processo(v_ID_PROCESSO, RA1, RA2, RA3) {
  $.ajax({
    type: "POST",
    url: "Banco/Verificar_aluno_processo.php",
    data: {
      PROCESSO: v_ID_PROCESSO,
      ALUNO1: RA1,
      ALUNO2: RA2,
      ALUNO3: RA3,
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      var v_ID_PROCESSO = json.ID_PROCESSO;
      fnc_mensagem_resposta(
        "Há outro processo com esse ra, processo:" + v_ID_PROCESSO
      );
    },
  });
}

function fnc_imprimir_rel_monitoria_I() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Acao_Monitoria_I.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_monitoria_II() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='text' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Acao_Monitoria_II.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_monitoria_III() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Acao_Monitoria-III.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_monitoria_IV() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Acao_Monitoria_IV.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_monitoria_V() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Acao_Monitoria_V.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_peticao_exec() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Peticao_Execucao.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_peticao_exec_II() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("Peticao_Execucao_II.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_ficha_andamento() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("FichaAndamento.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_ficha_andamento_ativ() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>" +
    "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
    "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
    "<input type='hidden' id='DATA' name='DATA' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("FichaAndamentoAtv.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());
  $("#ESTAGIARIO").val($("#txt_estagiario").val());
  $("#NUM_OAB").val($("#txt_estagiario").val());
  $("#DATA").val($("#txt_data_rel").val());

  $("#formIndex").submit();
}

function fnc_imprimir_rel_procuracao() {
  $("#formIndex").empty();
  var v_imput =
    "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
    "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
    "<input type='hidden' id='PROCESSO' name='PROCESSO' value=''>";

  $(v_imput).appendTo("#formIndex");

  $("#RELATORIO").val("procuracao.rpt");
  $("#PROCESSO").val($("#txt_cod_andamento").val());

  $("#formIndex").submit();
}

function fnc_limpar_campos() {
  $("#txt_cod_reu").val("");
  $("#txt_nome_reu").val("");
  $("#txt_cod_andamento").val("");
  $("#txt_dt_cadastro").val("");
  $("#txt_cod_advogado").val("");
  $("#txt_nome_advogado").val("");
  $("#txt_cod_acao").val("");
  $("#txt_nome_acao").val("");
  $("#txt_data_dist").val("");
  $("#txt_vara").val("");
  $("#txt_n_processo").val("");
  $("#txt_apenso_1").val("");
  $("#txt_cod_autor").val("");
  $("#txt_nome_autor").val("");
  $("#txt_deb_ano").val("");
  $("#txt_mes_ini").val("");
  $("#txt_mes_fim").val("");
  $("#txt_valor_desc").val("");
  $("#txt_total_divida").val("");
  $("#txt_acordo").val("");
  $("#txt_ficha").val("");
  $("#txt_data_rel").val("");
  $("#txt_estagiario").val("");
  limparAlunosDinamicos();
}

function modal_parametros(a) {
  $("#tipo_relat").val(a);
  var doc_Modal = "";
  doc_Modal = $("#modal_parametro");

  doc_Modal
    .kendoWindow({
      title: "PARAMETROS",
      modal: true,
      width: "30%",

      resizable: false,
      visible: false,

      actions: ["Pin", "Close", "Maximize"],
    })
    .data("kendoWindow")
    .center()
    .open();
}

function fnc_Imprimir_rel() {
  var b = $("#tipo_relat").val();

  if (b == "s1") {
    $("#formIndex").empty();
    var v_imput =
      "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
      "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
      "<input type='hidden' id='NUM_ACORDO' name='NUM_ACORDO' value=''>" +
      "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
      "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
      "<input type='hidden' id='TEM_ENTRADA' name='TEM_ENTRADA' value=''>";

    $(v_imput).appendTo("#formIndex");

    $("#RELATORIO").val("Anchi_rel_peticao_monitoria_suspensao_I.rpt");
    $("#NUM_ACORDO").val($("#p_acordo").val());
    $("#NUM_OAB").val($("#txt_cod_advogado").val());
    $("#ESTAGIARIO").val($("#txt_estagiario").val());
    $("#TEM_ENTRADA").val($("#txt_entrada").val());
    $("#formIndex").submit();
    $("#tipo_relat").val("");
  }

  if (b == "s2") {
    $("#formIndex").empty();
    var v_imput =
      "<input type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
      "<input type='hidden' id='BANCO' name='BANCO' value='1'>" +
      "<input type='hidden' id='NUM_ACORDO' name='NUM_ACORDO' value=''>" +
      "<input type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
      "<input type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>" +
      "<input type='hidden' id='TEM_ENTRADA' name='TEM_ENTRADA' value=''>";

    $(v_imput).appendTo("#formIndex");

    $("#RELATORIO").val("Anchi_rel_peticao_monitoria_suspensao_II.rpt");
    $("#NUM_ACORDO").val($("#p_acordo").val());
    $("#NUM_OAB").val($("#txt_cod_advogado").val());
    $("#ESTAGIARIO").val($("#txt_estagiario").val());
    $("#TEM_ENTRADA").val($("#txt_entrada").val());
    $("#formIndex").submit();
  }

  if (b == "e1") {
    $("#formIndex2").empty();
    var v_imput =
      "<input  type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
      "<input  type='hidden' id='BANCO' name='BANCO' value=''>" +
      "<input  type='hidden' id='NUM_ACORDO' name='NUM_ACORDO' value=''>" +
      "<input  type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
      "<input  type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>";

    $(v_imput).appendTo("#formIndex2");

    $("#RELATORIO").val("Anchi_rel_extincao_I.rpt");
    $("#NUM_ACORDO").val($("#p_acordo").val());
    $("#NUM_OAB").val($("#txt_cod_advogado").val());
    $("#ESTAGIARIO").val($("#txt_estagiario").val());
    $("#formIndex2").submit();
  }

  if (b == "e2") {
    $("#formIndex2").empty();
    var v_imput =
      "<input  type='hidden' id='RELATORIO' name='RELATORIO' value=''>" +
      "<input  type='hidden' id='BANCO' name='BANCO' value=''>" +
      "<input  type='hidden' id='NUM_ACORDO' name='NUM_ACORDO' value=''>" +
      "<input  type='hidden' id='NUM_OAB' name='NUM_OAB' value=''>" +
      "<input  type='hidden' id='ESTAGIARIO' name='ESTAGIARIO' value=''>";

    $(v_imput).appendTo("#formIndex2");

    $("#RELATORIO").val("Anchi_rel_extincao_II.rpt");
    $("#NUM_ACORDO").val($("#p_acordo").val());
    $("#NUM_OAB").val($("#txt_cod_advogado").val());
    $("#ESTAGIARIO").val($("#txt_estagiario").val());
    $("#formIndex2").submit();
  }
}

// ============================================
// NOVAS FUNÇÕES PARA GERAÇÃO DINÂMICA DE DOCUMENTOS
// ============================================

/**
 * Adiciona um novo conjunto de inputs (Modelo, Categoria, Subcategoria)
 */
function adicionarNovaSelecao() {
  selectionCounter++;
  const selectionId = `selection-${selectionCounter}`;
  
  // Apenas a primeira seleção terá o campo Modelo
  const incluirModelo = (selectionCounter === 1);

  const selectionHTML = `
    <div class="selection-group" id="${selectionId}" data-selection-id="${selectionCounter}">
      <div class="selection-group-header">
        <span class="selection-group-title">Seleção #${selectionCounter}</span>
        ${selectionCounter > 1 ? `
        <button class="btn-remove-selection" onclick="removerSelecao('${selectionId}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
          Remover
        </button>
        ` : ''}
      </div>
      
      <div class="selection-inputs">
        ${incluirModelo ? `
        <div class="form-group">
          <label class="form-label">Modelo</label>
          <input id="modelo-${selectionCounter}" class="form-control modelo-select" data-selection="${selectionCounter}" />
        </div>` : ''}
        
        <div class="form-group">
          <label class="form-label">Categoria</label>
          <input id="categoria-${selectionCounter}" class="form-control categoria-select" data-selection="${selectionCounter}" />
        </div>
        
        <div class="form-group">
          <label class="form-label">Subcategoria</label>
          <input id="subcategoria-${selectionCounter}" class="form-control subcategoria-select" data-selection="${selectionCounter}" />
        </div>
      </div>
    </div>
  `;
  
  $('#dynamic-selections-container').append(selectionHTML);
  
  // Inicializar os dropdowns do Kendo (modelos somente se o elemento existir)
  inicializarDropdowns(selectionCounter);
  
  // Adicionar ao array de dados
  selectionsData.push({
    id: selectionCounter,
    modelo: null,
    link: null,
    categoria: null,
    categoriaTexto: null,
    subcategoria: null,
    texto: null
  });
}

/**
 * Remove um conjunto de seleção
 */
function removerSelecao(selectionId) {
  const selectionElement = $(`#${selectionId}`);
  const dataId = selectionElement.data('selection-id');
  // Não permitir remover a primeira seleção
  if (dataId === 1) {
    return;
  }
  
  // Remover do array de dados
  selectionsData = selectionsData.filter(s => s.id !== dataId);
  
  // Remover elemento visual com animação
  selectionElement.fadeOut(300, function() {
    $(this).remove();
    
    // Renumerar as seleções restantes
    renumerarSelecoes();
  });
}

/**
 * Renumera as seleções após remoção
 */
function renumerarSelecoes() {
  // Atualiza títulos e sincroniza o array selectionsData com a ordem atual do DOM
  const novoSelections = [];
  $('.selection-group').each(function(index) {
    const newIndex = index + 1;
    $(this).find('.selection-group-title').text(`Seleção #${newIndex}`);
    // Atualiza atributo data-selection-id e ids dos inputs
    $(this).attr('data-selection-id', newIndex);
    const oldId = $(this).attr('id');
    const newId = `selection-${newIndex}`;
    $(this).attr('id', newId);


    const header = $(this).find('.selection-group-header');
    const btn = header.find('.btn-remove-selection');
    if (newIndex > 1) {
      if (!btn.length) {
        header.append(`
          <button class="btn-remove-selection" onclick="removerSelecao('${newId}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
            Remover
          </button>
        `);
      } else {
        // atualizar onclick para novo id
        btn.attr('onclick', `removerSelecao('${newId}')`);
      }
    } else {
      // remover botão se existir
      if (btn.length) {
        btn.remove();
      }
    }

    // Atualiza ids dos inputs dentro do grupo se existirem
    const modeloInput = $(this).find('[id^="modelo-"]');
    if (modeloInput.length) {
      modeloInput.attr('id', `modelo-${newIndex}`);
      modeloInput.attr('data-selection', newIndex);
    }
    const categoriaInput = $(this).find('[id^="categoria-"]');
    if (categoriaInput.length) {
      categoriaInput.attr('id', `categoria-${newIndex}`);
      categoriaInput.attr('data-selection', newIndex);
    }
    const subInput = $(this).find('[id^="subcategoria-"]');
    if (subInput.length) {
      subInput.attr('id', `subcategoria-${newIndex}`);
      subInput.attr('data-selection', newIndex);
    }

    // Garantir que apenas a primeira seleção tenha o campo Modelo
    if (newIndex === 1) {
      if (!$(this).find('[id^="modelo-"]').length) {
        // Inserir bloco de modelo antes da primeira .form-group (categoria)
        $(this).find('.selection-inputs').prepend(`
          <div class="form-group">
            <label class="form-label">Modelo</label>
            <input id="modelo-${newIndex}" class="form-control modelo-select" data-selection="${newIndex}" />
          </div>
        `);
        inicializarModelos(newIndex);
      } else {
        // Se existir elemento, garantir que o kendo esteja inicializado
        const modeloElem = $(this).find(`#modelo-${newIndex}`);
        if (modeloElem.length && !modeloElem.data('kendoDropDownList')) {
          inicializarModelos(newIndex);
        }
      }
    } else {
      // Se não for a primeira, remover o campo modelo caso exista
      const modeloElemOld = $(this).find('[id^="modelo-"]');
      if (modeloElemOld.length) {
        const ddOld = modeloElemOld.data('kendoDropDownList');
        if (ddOld) ddOld.destroy();
        modeloElemOld.closest('.form-group').remove();
      }
    }

    // Tenta encontrar os dados correspondentes no selectionsData pelo antigo id (se houver)
    const antigoDataId = parseInt(oldId && oldId.split('-')[1], 10);
    const encontrado = selectionsData.find(s => s.id === antigoDataId);
    if (encontrado) {
      encontrado.id = newIndex;
      novoSelections.push(encontrado);
    } else {
      // Se não encontrou, cria um novo objeto padrão
      novoSelections.push({ id: newIndex, modelo: null, categoria: null, subcategoria: null, texto: null });
    }
  });

  // Substitui selectionsData pela nova ordem
  selectionsData = novoSelections;
}

/**
 * Inicializa os dropdowns do Kendo UI para uma seleção específica
 */
function inicializarDropdowns(selectionId) {
  // Dropdown de Modelos (somente se o input de modelo existir)
  if ($(`#modelo-${selectionId}`).length) {
    inicializarModelos(selectionId);
  }

  // Dropdown de Categorias
  inicializarCategorias(selectionId);
}

/**
 * Inicializa dropdown de Modelos
 */
function inicializarModelos(selectionId) {
  const modeloDataSource = new kendo.data.DataSource({
    transport: {
      read: {
        url: "Banco/carregarModelos.php",
        cache: false
      }
    },
    schema: {
      data: "data_grid",
      model: {
        id: "ID_MODELO",
        fields: {
          ID_MODELO: { type: "number" },
          NOME: { type: "string" },
          LINK: { type: "string" }
        }
      }
    }
  });
  
  $(`#modelo-${selectionId}`).kendoDropDownList({
    dataTextField: "NOME",
    dataValueField: "ID_MODELO",
    dataSource: modeloDataSource,
    optionLabel: "Selecione um modelo...",
    change: function(e) {
      const value = this.value()
      const dataItem = this.dataItem()
      const link = dataItem ? dataItem.LINK : null
      const currentId = parseInt(this.element.attr('data-selection'), 10)
      atualizarSelectionData(currentId, 'modelo', value)
      atualizarSelectionData(currentId, 'modeloLink', link)
    }
  });
}

/**
 * Inicializa dropdown de Categorias
 */
function inicializarCategorias(selectionId) {
  const categoriaDataSource = new kendo.data.DataSource({
    transport: {
      read: {
        url: "Banco/carregarGrupo.php",
        data: {
          COD_GRUPO: null,
          ID_PROCESSO: function() {
            return $("#txt_cod_andamento").val();
          }
        },
        cache: false
      }
    },
    schema: {
      data: "DATA",
      model: {
        fields: {
          VALOR: { type: "string" },
          DESCRICAO: { type: "string" }
        }
      }
    }
  });
  
  $(`#categoria-${selectionId}`).kendoDropDownList({
    dataTextField: "DESCRICAO",
    dataValueField: "VALOR",
    dataSource: categoriaDataSource,
    optionLabel: "Selecione uma categoria...",
    filter: "contains",
    change: function(e) {
      const value = this.value();
      const text = this.text()
      const currentId = parseInt(this.element.attr('data-selection'), 10);
      atualizarSelectionData(currentId, 'categoria', value)
      atualizarSelectionData(currentId, 'categoriaTexto', text)
      
      // Atualizar subcategorias baseado na categoria selecionada
      inicializarSubcategorias(currentId, value);
    }
  });
}

/**
 * Inicializa dropdown de Subcategorias
 */
function inicializarSubcategorias(selectionId, categoriaId) {
  const subcategoriaDataSource = new kendo.data.DataSource({
    transport: {
      read: {
        url: "Banco/carregarGrupo.php",
        data: {
          COD_GRUPO: categoriaId,
          ID_PROCESSO: $("#txt_cod_andamento").val()
        },
        cache: false
      }
    },
    schema: {
      data: "DATA",
      model: {
        fields: {
          VALOR: { type: "string" },
          DESCRICAO: { type: "string" }
        }
      }
    }
  });
  
  // Destruir dropdown existente se houver
  const dropdown = $(`#subcategoria-${selectionId}`).data("kendoDropDownList");
  if (dropdown) {
    dropdown.destroy();
  }
  
  $(`#subcategoria-${selectionId}`).kendoDropDownList({
    dataTextField: "DESCRICAO",
    dataValueField: "VALOR",
    dataSource: subcategoriaDataSource,
    optionLabel: "Selecione uma subcategoria...",
    filter: "contains",
    change: function(e) {
      const dropdownValue = this.value();  // VALOR (HTML)
      const dropdownText = this.text();     // DESCRICAO
      const currentId = parseInt(this.element.attr('data-selection'), 10);

      // Obtém o dataItem selecionado diretamente do Kendo
      const itemSelecionado = this.dataItem();

      if (itemSelecionado) {
        // Extrai o ID_SUB_GRUPO
        const idSubGrupo = itemSelecionado.ID_SUB_GRUPO;

        // Atualiza o selectionData com todos os dados 
        atualizarSelectionData(currentId, 'subcategoriaId', idSubGrupo);
        atualizarSelectionData(currentId, 'subcategoriaTexto', dropdownValue);

        // Log para verificar
        console.log("Subcategoria selecionada:", {
          nome: dropdownText,
          id: idSubGrupo,
          valor: dropdownValue
        });

        // Mostrar preview do texto
        mostrarPreviewTexto(dropdownText);
      }
    }
  });
}

/**
 * Atualiza os dados da seleção
 */
function atualizarSelectionData(selectionId, field, value) {
  const selection = selectionsData.find(s => s.id === selectionId);
  if (selection) {
    selection[field] = value;
  }
}

/**
 * Mostra preview do texto selecionado
 */
function mostrarPreviewTexto(texto) {
  $('#texto-preview-container').hide();
  $('#texto-preview-content').html(texto || '');
}

/**
 * Limpa todas as seleções
 */
function limparSelecoes() {
  if (confirm('Deseja realmente limpar todas as seleções?')) {
    $('#dynamic-selections-container').empty();
    selectionsData = [];
    selectionCounter = 0;
    $('#texto-preview-container').hide();
    $('#texto-preview-content').empty();
  }
}

/**
 * Gera o documento Word com as novas seleções
 */
/**
 * Gera o documento Word com as novas seleções
 */
/* ============================
   LOADING OVERLAY - Bloqueio de tela
   ============================ */

function mostrarLoadingWord() {
  // Bloqueia o recarregamento da página
  window._wordBeforeUnload = function (e) {
    e.preventDefault();
    e.returnValue = "O documento ainda está sendo gerado. Deseja realmente sair?";
    return e.returnValue;
  };
  window.addEventListener("beforeunload", window._wordBeforeUnload);

  let overlay = document.getElementById("word-loading-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "word-loading-overlay";
    overlay.className = "word-loading-overlay";
    document.body.appendChild(overlay);
  }

  overlay.innerHTML = `
    <div class="word-loading-popup">
      <div class="word-loading-icon-wrapper">
        <div class="word-loading-ring"></div>
        <svg class="word-loading-doc-icon" viewBox="0 0 48 48" fill="none">
          <rect x="8" y="4" width="32" height="40" rx="4" fill="#185ABD" opacity="0.12" stroke="#185ABD" stroke-width="2"/>
          <text x="24" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="#185ABD" font-family="Arial, sans-serif">W</text>
          <rect x="14" y="34" width="20" height="2" rx="1" fill="#185ABD" opacity="0.3"/>
        </svg>
      </div>
      <h3 class="word-loading-title">Gerando Documento</h3>
      <p class="word-loading-message">Aguarde enquanto seu documento Word está sendo preparado...</p>
      <div class="word-loading-bar-track">
        <div class="word-loading-bar-fill"></div>
      </div>
      <span class="word-loading-hint">Não feche ou recarregue a página</span>
    </div>
  `;
}

function esconderLoadingWord() {
  // Remove o bloqueio de recarregamento
  if (window._wordBeforeUnload) {
    window.removeEventListener("beforeunload", window._wordBeforeUnload);
    delete window._wordBeforeUnload;
  }

  const overlay = document.getElementById("word-loading-overlay");
  if (overlay) {
    overlay.classList.add("word-loading-overlay-closing");
    setTimeout(() => overlay.remove(), 300);
  }
}


/* ============================
   FUNÇÃO PRINCIPAL
   ============================ */

function geraDocWordNovo() {
  console.log(selectionsData);
  if (selectionsData.length === 0) {
    popupNotification.show({
      title: "<b>Atenção</b>",
      message: "Adicione pelo menos uma seleção antes de gerar o documento!"
    }, "info");
    return;
  }

  // Exigir 'modelo' apenas para a primeira seleção; as demais só precisam de categoria e subcategoria
  const incomplete = selectionsData.filter((s, idx) => {
    if (idx === 0) {
      return !s.modelo || !s.categoria || !s.subcategoriaId;
    }
    return !s.categoria || !s.subcategoriaId;
  });
  if (incomplete.length > 0) {
    popupNotification.show({
      title: "<b>Atenção</b>",
      message: "Preencha todos os campos obrigatórios nas seleções!"
    }, "warning");
    return;
  }

  // Monta o array de seções a partir de TODAS as seleções
  const secoes = selectionsData.map((selection, idx) => {
    return {
      ordem: idx + 1,
      categoria: selection.categoriaTexto,
      subcategoria: selection.subcategoriaTexto
    };
  });

  // 1) Mostra a tela de loading
  mostrarLoadingWord();

  // 2) Busca variáveis do backend e coleta valores do DOM
  buscarVariaveisEColetarDados()
    .then(dados => {
      // 3) Envia POST único com todas as seções usando Fetch API
      return fetch("http://localhost:5026/documentos/gerar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          tipo_documento: selectionsData[0].modeloLink,
          dados: dados,
          formato: "docx",
          secoes: secoes
        })
      });
    })
    .then(res => {
      if (!res.ok) {
        return res.json().then(errData => {
          throw errData;
        });
      }
      
      // Extrai o nome do arquivo do header
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename[^;=\n]*=(?:(['"]).*?\1|[^;\n]*)/);
      const filename = match ? match[0].split("=")[1].replace(/['"]/g, "") : "documento.docx";
      
      return res.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      esconderLoadingWord();

      const blobUrl = URL.createObjectURL(blob);
      mostrarPreviewWord(blobUrl, filename);

      popupNotification.show({
        title: "<b>Sucesso</b>",
        message: "Documento gerado com sucesso!"
      }, "success");
    })
    .catch(err => {
      esconderLoadingWord();

      let msg = "Falha ao gerar documento!";
      if (err && err.msg) msg = err.msg;
      else if (err && err.detail) msg = err.detail;
      else if (typeof err === "string") msg = err;

      popupNotification.show({
        title: "<b>Erro</b>",
        message: msg
      }, "error");

      console.error("Erro na geração do documento:", err);
    });
}


//console.log("selectionsData[0]:", selectionsData[0]);


function mostrarPreviewWord(wordUrl, nomeArquivo) {
  let overlay = document.getElementById("word-preview-overlay");

  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "word-preview-overlay";
    overlay.className = "word-overlay";
    document.body.appendChild(overlay);
  }

  // Extrair extensão e tamanho formatado do nome
  const extensao = nomeArquivo.split('.').pop().toUpperCase();

  overlay.innerHTML = `
    <div class="word-popup word-popup-preview">
      <div class="word-popup-header">
        <svg class="word-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        <div class="word-header-info">
          <h3>Documento Gerado</h3>
          <span class="word-filename">${nomeArquivo}</span>
        </div>
        <button class="word-btn-close" onclick="esconderPreviewWord()" title="Fechar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="word-popup-body">
        <div class="word-file-card">
          <div class="word-file-icon-wrapper">
            <svg class="word-file-icon" viewBox="0 0 48 48" fill="none">
              <rect x="4" y="2" width="40" height="44" rx="4" fill="#185ABD" opacity="0.1" stroke="#185ABD" stroke-width="2"/>
              <path d="M14 2V0" stroke="none"/>
              <text x="24" y="28" text-anchor="middle" font-size="11" font-weight="700" fill="#185ABD" font-family="Arial, sans-serif">W</text>
              <rect x="12" y="34" width="24" height="2" rx="1" fill="#185ABD" opacity="0.3"/>
              <rect x="16" y="38" width="16" height="2" rx="1" fill="#185ABD" opacity="0.2"/>
            </svg>
          </div>
          <div class="word-file-details">
            <span class="word-file-name">${nomeArquivo}</span>
            <span class="word-file-type">Documento Microsoft Word (.${extensao.toLowerCase()})</span>
          </div>
          <div class="word-file-badge">${extensao}</div>
        </div>

        <div class="word-info-message">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <span>Faça o download para visualizar o documento no Word.</span>
        </div>
      </div>

      <div class="word-popup-footer">
        <button class="word-btn word-btn-download" onclick="baixarWord('${wordUrl}', '${nomeArquivo}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Baixar Documento
        </button>
        <button class="word-btn word-btn-cancel" onclick="esconderPreviewWord()">
          Fechar
        </button>
      </div>
    </div>
  `;

  // Fechar ao clicar no overlay (fundo escuro)
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) esconderPreviewWord();
  });
}


function baixarWord(wordUrl, nomeArquivo) {
  const btnDownload = document.querySelector(".word-btn-download");
  if (btnDownload) {
    btnDownload.disabled = true;
    btnDownload.innerHTML = `
      <svg class="word-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
      </svg>
      Baixando...
    `;
  }

  fetch(wordUrl)
    .then(res => res.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = nomeArquivo;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      if (btnDownload) {
        btnDownload.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          Download Concluído!
        `;
        btnDownload.classList.add("word-btn-success");
      }

      setTimeout(() => {
        // esconderPreviewWord();
      }, 1500);
    })
    .catch(err => {
      console.error("Erro ao baixar documento:", err);

      if (btnDownload) {
        btnDownload.disabled = false;
        btnDownload.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Baixar Documento
        `;
      }

      if (typeof popupNotification !== "undefined") {
        popupNotification.show({
          title: "<b>Erro</b>",
          message: "Falha ao baixar o documento!"
        }, "error");
      }
    });
}


function esconderPreviewWord() {
  const overlay = document.getElementById("word-preview-overlay");
  if (overlay) {
    overlay.classList.add("word-overlay-closing");
    setTimeout(() => overlay.remove(), 300);
  }
}


// ============================================
// FUNÇÕES ANTIGAS MANTIDAS PARA COMPATIBILIDADE
// (Funções do editor antigo - caso ainda sejam usadas em outro lugar)
// ============================================

function abrirModalNovoDocumento() {
  // Manter função antiga para não quebrar outras partes do sistema
  // Mas redirecionar para nova funcionalidade
  limparSelecoes();
  adicionarNovaSelecao();
}

function geraNovoEditor(id) {
  // Função mantida para compatibilidade
  $("#editor-" + id).kendoEditor({
    tools: [
      "bold",
      "italic",
      "underline",
      "strikethrough",
      "justifyLeft",
      "justifyCenter",
      "justifyRight",
      "justifyFull",
      {
        name: "custom",
        tooltip: "Insert a horizontal rule",
        exec: function (e) {
          var editor = $(this).data("kendoEditor");
          editor.exec("inserthtml", { value: "<br />" });
        },
      },
    ],
  });
}

function regarregaComboPorTarget(id) {
  if (id != "contentAppend") {
    let id_ = id.replace("_1", "");
    Carregarcombo_estagiario = new kendo.data.DataSource({
      batch: true,
      transport: {
        read: {
          url: "Banco/carregarGrupo.php",
          cache: false,
          data: {
            COD_GRUPO: $("#" + id_).val(),
            ID_PROCESSO: $("#txt_cod_andamento").val(),
          },
        },
      },
      batch: false,
      schema: {
        data: "DATA",
        model: {
          id: "ID_PESSOA",
          fields: {
            ID_PESSOA: { nullable: true },
            NOME: { nullable: true },
          },
        },
      },
    });

    $("#" + id).kendoDropDownList({
      dataTextField: "DESCRICAO",
      dataValueField: "VALOR",
      dataSource: Carregarcombo_estagiario,
      filter: "contains",
      change: (e) => {
        e.preventDefault();
        regarregaComboPorTarget(id + "_1");
        let new_id_ = id.replace("grupo_selection-", "");

        selecionaTexto(new_id_);
      },
      optionLabel: "Selecione...",
    });
  }
}

function selecionaTexto(_id) {
  let id = _id.replace("_1", "");
  var editor = $("#editor-" + id).data("kendoEditor");
  if (editor) {
    editor.value($("#grupo_selection-" + id + "_1").val());
  }
}

function geraAppendNovaSeccao() {
  let node_actual = document.getElementsByName("editorView");
  node_actual = node_actual.length;
  $(".contentAppend").append(`<div name="group" class="group">
  <div class="bodyHeader">
	  <div class="row">
		  <div class="col-md-6">
			  <div>
				  Grupo
			  </div>
			  <input id="grupo_selection-${
          node_actual + 1
        }" name="" class="k-textbox"  style="width:360px" />
		  </div>
		  <div class="col-md-6">
			  <div>
				  Sub-Grupo
			  </div>
			  <input id="grupo_selection-${
          node_actual + 1
        }_1" name="" class="k-textbox" style="width:360px" />
		  </div>
		 
	  </div>

	  <div class="col-md-8" style="padding-left: 15px;padding-right: 15px;">
	  		<div class="seccao">Secção ${node_actual + 1}</div>
		  		<textarea name="editorView" id="editor-${
            node_actual + 1
          }" cols="40" rows="20"></textarea>	  			</div>
  			</div>
		</div>
	</div>
	<div class="border"></div>`);
  geraNovoEditor(node_actual + 1);
  regarregaComboPorTarget("grupo_selection-" + (node_actual + 1));
  regarregaComboPorTarget("grupo_selection-" + (node_actual + 1) + "_1");
  $("html, body").animate(
    {
      scrollTop: 800 * (node_actual + 1),
    },
    500
  );
}

// Função antiga de gerar documento Word
function geraDocWord() {
  let node_actual = document.getElementsByName("editorView");
  node_actual = node_actual.length;

  let objEnvio = [],
    DATA;

  var editorAtual,
    chave = 1;
  for (let index = 1; index <= node_actual; index++) {
    editorAtual = $("#editor-" + index).val();
    valorUsado = editorAtual.split("&lt;br /&gt;");
    valorUsado.forEach((Element, index) => {
      DATA = {
        id: chave,
        html: Element,
      };
      chave++;
      objEnvio.push(DATA);
    });
  }

  $.ajax({
    type: "POST",
    url: "word/gerador.php",
    data: {
      DATA: objEnvio,
      ID_PROCESSO: $("#txt_cod_andamento").val(),
      MODELO: $("#txt_DOCS").val(),
      ALUNOS: obterRAsAlunos(),
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      d = new Date();
      d.getTime();
      download(json, "doc_jud_" + d.getTime() + "_1-1");
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Erro</b>",
          message: "falha ao gerar documento!",
        },
        "info"
      );
    },
  });
}

function adicionarImagem() {
  let PRE_ACORDO = 1239;
  let ALUNO = 2392;

  $("#addDocumento").remove();
  $("#divWindow").append('<div id="addDocumento"></div>');

  let myWindow = $("#addDocumento");

  myWindow
    .kendoWindow({
      title: "Anexar Novo Documento",
      actions: ["Close"],
      modal: true,
      resizable: false,
    })
    .data("kendoWindow")
    .open()
    .content(
      '<div><h3>Selecione novo o documento modelo<span style="color: red; font-size:10px; margin-left: 15px; "> lembre-se apenas formatos .docx são permitidos</span></h3><input name="files" id="files" class="files" type="file"  data-role="upload" autocomplete="off">'
    )
    .center();

  $(".files").kendoUpload({
    showFileList: true,
    multiple: false,
    batch: false,
    showFileList: true,
    async: {
      autoUpload: false,
      saveUrl: "word/upload.php",
    },
    validation: {
      allowedExtensions: [".docx"],
      maxFileSize: 100000000,
    },
    localization: {
      select: "Selecione o arquivo",
      headerStatusUploaded: " ",
      headerStatusUploading: "Carregando...",
      dropFilesHere: "Arraste as imagens aqui",
      uploading: "Carregando ...",
      invalidFileExtension: "Anexe apenas arquivos .docx",
    },
    error: function (e) {},
    success: function (e) {
      $("#addDocumento").data("kendoWindow").close();
      carregarModelo();
    },
  });
}

function download(uri, nome) {
  var link = document.createElement("a");
  link.download = nome;
  link.href = uri;
  link.click();
}

//GRID COMPLETO
function Carregar_Grid_modelos() {
  CarregarGrid = new kendo.data.DataSource({
    batch: true,
    transport: {
      read: {
        url: "Banco/carregarGruposGrid.php",
        data: {},
        cache: false,
      },

      update: {
        async: false,
        url: "Banco/editaCategoria.php",
        cache: false,
        complete: function (e) {
          $("#div_grid_assuntos").data("kendoGrid").dataSource.read();
        },
      },
      create: {
        async: false,
        url: "Banco/criaCategoria.php",
        cache: false,
        complete: function (e) {
          $("#div_grid_assuntos").data("kendoGrid").dataSource.read();
        },
      },
      destroy: {
        async: false,
        url: "Banco/xxxxxxx.php",
        cache: false,
        complete: function (e) {
          fnc_mensagem_resposta(e);
        },
      },
      cache: false,
    },
    pageSize: 50,
    batch: false,
    schema: {
      data: "data_grid",

      model: {
        id: "ID_ASSUNTO",
        fields: {
          ID_ASSUNTO: { nullable: false, editable: false },
          DESCRICAO: { nullable: false, editable: true },
        },
      },
    },
  });

  $("#div_grid_assuntos").kendoGrid({
    dataSource: CarregarGrid,
    scrollable: false,
    sortable: false,
    reorderable: false,
    resizable: false,

    navigable: false,
    allowCopy: false,
    groupable: false,

    columnMenu: {
      messages: {
        sortAscending: "Ascendente",
        sortDescending: "Descendente",
        filter: "Filtro",
        columns: "Colunas",
      },
    },
    filterable: {
      messages: {
        info: "Título:",
        filter: "Filtrar",
        clear: "Limpar",
        isTrue: "é verdadeiro",
        isFalse: "é falso",
        and: "E",
        or: "Ou",
      },
      operators: {
        string: {
          eq: "Igual a",
          neq: "Diferente de",
          startswith: "Começa com",
          contains: "Contém",
          endswith: "Termina em",
        },
        number: {
          eq: "Igual a",
          neq: "Diferente de",
          gte: "Maior que ou igual a",
          gt: "Mair que",
          lte: "Menor que ou igual a",
          lt: "Menor que",
        },
        date: {
          eq: "Igual a",
          neq: "Diferente de",
          gte: "Maior que ou igual a",
          gt: "Mair que",
          lte: "Menor que ou igual a",
          lt: "Menor que",
        },
      },
    },
    pageable: {
      refresh: true,
      pageSizes: [100, 200, 300, 400, 500, 1000],
      numeric: true,
      buttonCount: 10,
      messages: {
        empty: "",
        page: "Páginas",
        itemsPerPage: "Itens por página",
        first: "Ir para primeira página",
        previous: "Voltar a página anterior",
        next: "Ir para a próxima página",
        last: "Ir para ultima página",
        refresh: "Atualizar",
      },
    },
    toolbar: [{ name: "create", text: "Novo" }],
    detailInit: detailInit,
    editable: {
      confirmation: "Deseja mesmo excluir",
      mode: "popup",
    },
    edit: function (e) {
      e.container.kendoWindow("title", "Agenda");
      $("a.k-grid-update")[0].innerHTML =
        "<span class='k-icon k-update'></span>Salvar";
      $("a.k-grid-cancel")[0].innerHTML =
        "<span class='k-icon k-cancel'></span> <span onclick='$(\"#div_grid\").data(\"kendoGrid\").dataSource.read();'>Cancelar</span> ";
      $("a.k-window-titlebar").hide();
      $("a.k-window-action").hide();
    },

    noRecords: {
      template:
        '<tr class="kendo-data-row"><td colspan="\' + colCount + \'" class="no-data">Nenhuma informação encontrada.</td></tr>',
    },
    columns: [
      { field: "ID_ASSUNTO", title: "ID CATEGORIA" },
      { field: "DESCRICAO", title: "CATEGORIA" },
      {
        command: [
          { name: "edit", text: "Editar" },
          { text: "Criar Sub-categoria", click: criaSubCategoria },
        ],
        title: "Opções",
        headerAttributes: { style: "text-align:center;" },
      },
    ],
    batch: true,
    schema: {
      model: { id: "id" },
    },
  });
}

//SUBGRID
function detailInit(e) {
  $("<div/>")
    .appendTo(e.detailCell)
    .kendoGrid({
      dataSource: {
        transport: {
          read: {
            url: "Banco/carregarGruposGridSub.php",
            data: {
              ID_ASSUNTO: e.data.ID_ASSUNTO,
            },
          },
          cache: false,
        },
        schema: {
          data: "data_grid2",
          model: {
            id: "ID_ASSUNTO",
            fields: {
              ID_ASSUNTO: { editable: false },
              ID_SUB_GRUPO: { editable: true },
              SUB_GRUPO: { editable: true },
              DESCRICAO: { editable: true },
            },
          },
        },
      },
      scrollable: false,
      noRecords: {
        template:
          '<tr class="kendo-data-row"><td colspan="\' + colCount + \'" class="no-data">Nenhuma disciplina cadastrada.</td></tr>',
      },

      columns: [
        {
          field: "SUB_GRUPO",
          title: "SUB GRUPO",
          headerAttributes: { style: "text-align:center;  font-weight: bold;" },
          encoded: false,
          attributes: { style: "text-align:center;" },
        },
        {
          field: "DESCRICAO",
          title: "DESCRICAO",
          headerAttributes: { style: "text-align:center;  font-weight: bold;" },
          encoded: false,
          attributes: { style: "text-align:center;" },
        },

        {
          command: [
            { name: "edit", text: "Editar", click: editaSubCategoria },
            { name: "custom", text: "excluir", click: removeSub },
          ],
          width: 400,
          title: "Opções",
        },
      ],
      batch: true,
      schema: {
        model: { id: "id" },
      },
    });
}

function carregarModelo() {
  Grid_Produtos = new kendo.data.DataSource({
    autoSync: false,
    transport: {
      read: {
        url: "Banco/carregarModelos.php",
        cache: false,
      },
      destroy: {
        url: "Banco/produto/excluirProdutos.php",
        type: "POST",
      },
      cache: false,
    },

    batch: false,
    schema: {
      data: "data_grid",
      model: {
        id: "ID_MODELO",
        fields: {
          ID_MODELO: { nullable: false },
          NOME: { nullable: false },
        },
      },
    },
  });
  //Parte do gerenciar Modelos de Documentos
  $("#gridDocsModelo").kendoGrid({
    dataSource: Grid_Produtos,
    scrollable: false,
    filterable: false,
    columns: [
      { field: "ID_MODELO", title: "ID" },

      {
        field: "NOME",
        title: "NOME",
      },
      {
        command: [{ name: "edit", text: "excluir", click: removeModelo }],
        title: "ações",
      },
    ],

    batch: true,
  });
}

function removeModelo(e) {
  e.preventDefault();

  var dataItem = this.dataItem($(e.currentTarget).closest("tr"));

  $.ajax({
    type: "POST",
    url: "Banco/removerModelo.php",
    data: {
      ID_MODELO: dataItem.ID_MODELO,
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      $("#gridDocsModelo").data("kendoGrid").dataSource.read();
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Atenção</b>",
          message: "erro ao remover!",
        },
        "info"
      );
    },
  });
}

function removeSub(e) {
  e.preventDefault();

  var dataItem = this.dataItem($(e.currentTarget).closest("tr"));

  $.ajax({
    type: "POST",
    url: "Banco/removerSub.php",
    data: {
      ID_ASSUNTO: dataItem.ID_ASSUNTO,
      ID_SUB_GRUPO: dataItem.ID_SUB_GRUPO,
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      $("#div_grid_assuntos").data("kendoGrid").dataSource.read();
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Atenção</b>",
          message: "erro ao remover!",
        },
        "info"
      );
    },
  });
}

function criaSubCategoria(e) {
  e.preventDefault();

  var dataItem = this.dataItem($(e.currentTarget).closest("tr"));

  ID_ASSUNTO = dataItem.ID_ASSUNTO;

  $("#appendEditor2").remove();
  $("#append2").append(
    '<div id="appendEditor2"><textarea name="" id="editor2" cols="50" rows="20"></textarea></div>'
  );

  $("#windowNovaSolicitacao")
    .kendoWindow({
      width: "35.5%",
      title: false,
      modal: true,
      visible: true,
      actions: ["Pin", "Minimize", "Maximize", "Close"],
    })
    .data("kendoWindow")
    .center()
    .open();

  $("#editor2").kendoEditor({
    tools: ["bold", "italic"],
  });
}

var ID_ASSUNTO, SUB_GRUPO, DESCRICAO, ID_SUB_GRUPO;

function editaSubCategoria(e) {
  var dataItem = this.dataItem($(e.currentTarget).closest("tr"));

  ID_ASSUNTO = dataItem.ID_ASSUNTO;
  SUB_GRUPO = dataItem.SUB_GRUPO;
  DESCRICAO = dataItem.DESCRICAO;
  ID_SUB_GRUPO = dataItem.ID_SUB_GRUPO;

  e.preventDefault();
  $("#appendEditor").remove();
  $("#append").append(
    '<div id="appendEditor"><textarea name="" id="editor" cols="50" rows="20"></textarea></div>'
  );

  $("#WINDOW_EDITA_GRUPO")
    .kendoWindow({
      width: "35.5%",
      title: false,
      modal: true,
      visible: true,
      actions: ["Pin", "Minimize", "Maximize", "Close"],
    })
    .data("kendoWindow")
    .center()
    .open();

  $("#editor").kendoEditor({
    tools: ["bold", "italic"],
  });

  var editor = $("#editor").data("kendoEditor");
  editor.value(DESCRICAO);
  $("#subgrupoEdit").val(SUB_GRUPO);
}

function salvarEditNovaSubCategoria() {
  $.ajax({
    type: "POST",
    url: "Banco/salvarSubGrupo.php",
    data: {
      ID_ASSUNTO: parseInt(ID_ASSUNTO),
      SUB_GRUPO: $("#subgrupoEdit").val(),
      DESCRICAO: $("#editor").val(),
      ID_SUB_GRUPO: parseInt(ID_SUB_GRUPO),
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      fecharJanelaEdit();
      $("#div_grid_assuntos").data("kendoGrid").dataSource.read();
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Atenção</b>",
          message: "erro ao salvar!",
        },
        "info"
      );
    },
  });
}

function salvarNovaSubCategoria() {
  let _sub_grupo = $("#ALUNO_SOL").val();
  let edit = $("#editor2").val();

  $.ajax({
    type: "POST",
    url: "Banco/InserirSubGrupo.php",
    data: {
      ID_ASSUNTO: parseInt(ID_ASSUNTO),
      SUB_GRUPO: _sub_grupo,
      DESCRICAO: edit,
    },
    cache: false,
    dataType: "json",
    success: function (json) {
      $("#div_grid_assuntos").data("kendoGrid").dataSource.read();
      fecharJanela();
    },
    error: function (json) {
      popupNotification.show(
        {
          title: "<b>Atenção</b>",
          message: "erro ao salvar!",
        },
        "info"
      );
    },
  });
}

function fecharJanela() {
  $("#windowNovaSolicitacao").data("kendoWindow").close();
}

function fecharJanelaEdit() {
  $("#WINDOW_EDITA_GRUPO").data("kendoWindow").close();
}



/*BUSCA DE VARIAVEIS PARA MONTAR O DOCUMENTO*/
function buscarVariaveisEColetarDados() {
  return new Promise((resolve, reject) => {
    // Extrai todas as subcategorias únicas de selectionsData
    const subcategorias = [...new Set(selectionsData.map(s => s.subcategoriaId))];
    
    // Array para armazenar todas as promises de busca
    const promises = subcategorias.map(subcategoria => {
      // Busca o texto da subcategoria correspondente
      const selecao = selectionsData.find(s => s.subcategoriaId === subcategoria);
      const subcategoriaId = selecao ? selecao.subcategoriaId : "";

      return new Promise((resolveSubcat, rejectSubcat) => {
        $.ajax({
          type: "POST",
          url: "https://app-teste.anchieta.br/Sistema_Juridico/Banco/carregarVariaveis.php",
          dataType: "json",
          data: {
            modelo: selectionsData[0].modelo,       // ← ID
            subcategoria: subcategoriaId              // ← ID
          },
          cache: false,
          success: function (response) {
            //console.log("Resposta bruta do backend:", response);

            // Valida se é um array
            let listaVariaveis = response;
            if (!Array.isArray(listaVariaveis)) {
              if (response.variáveis && Array.isArray(response.variáveis)) {
                listaVariaveis = response.variáveis;
              } else if (response.data && Array.isArray(response.data)) {
                listaVariaveis = response.data;
              } else if (response.resultado && Array.isArray(response.resultado)) {
                listaVariaveis = response.resultado;
              } else {
                rejectSubcat(`Resposta inválida para subcategoria ${subcategoriaId}`);
                return;
              }
            }

            const dados = {};

            listaVariaveis.forEach(variavel => {
              const tipoVar = variavel.TIPO_VARIAVEL || variavel.tipo_variavel;
              const origem = variavel.ORIGEM || variavel.origem;

              if (!origem) return;

              const elemento = document.getElementById(origem);

              if (elemento) {
                const valor = (elemento.value || "").trim();
                dados[tipoVar] = valor;
              } else {
                // Valor literal (ex: GETDATE(), JUNDIAÍ)
                dados[tipoVar] = origem;
              }
            });

            resolveSubcat({ subcategoria: subcategoriaId, dados });
          },
          error: function (xhr) {
            const msg = xhr.responseJSON?.detail || `Falha ao buscar variáveis da subcategoria ${subcategoriaId}!`;
            console.error("Erro ao buscar variáveis:", msg, xhr);
            rejectSubcat(msg);
          }
        });
      });
    });

    // Aguarda todas as buscas completarem
    Promise.all(promises)
      .then(resultados => {
        const dadosConsolidados = {};

        resultados.forEach(({ subcategoria, dados }) => {
          dadosConsolidados[subcategoria] = dados;
        });

        //console.log("Dados consolidados por subcategoria:", dadosConsolidados);
        resolve(dadosConsolidados);
      })
      .catch(err => {
        reject(err);
      });
  });
}

/* ============================
   VALIDAÇÃO DOS DADOS COLETADOS
   ============================ */

/**
 * Verifica se há campos obrigatórios vazios nos dados coletados.
 * Retorna um array com os IDs dos campos vazios.
 * Se o backend retornar um campo "obrigatorio" / "OBRIGATORIO",
 * ele será usado; caso contrário, todos são considerados opcionais.
 */
function validarDadosColetados(dados, listaVariaveis) {
  const camposVazios = [];

  listaVariaveis.forEach(variavel => {
    const origem = variavel.ORIGEM || variavel.origem;
    const obrigatorio = variavel.OBRIGATORIO || variavel.obrigatorio;

    if (obrigatorio && origem && dados.hasOwnProperty(origem)) {
      if (!dados[origem]) {
        camposVazios.push(origem);
      }
    }
  });

  return camposVazios;
}

// ============================================
// BLUR OVERLAY - Seções em Desenvolvimento
// ============================================

(function injetarEstilosBlurDev() {
  const style = document.createElement('style');
  style.textContent = `
    .dev-blur-wrapper {
      position: relative !important;
    }
    .dev-blur-overlay {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      background: rgba(255, 255, 255, 0.55);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100;
      border-radius: inherit;
    }
    .dev-blur-msg {
      background: rgba(255, 255, 255, 0.92);
      padding: 14px 24px;
      border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: #64748b;
      border: 1px solid #e2e8f0;
      user-select: none;
    }
    .dev-blur-msg svg {
      flex-shrink: 0;
      color: #94a3b8;
    }
  `;
  document.head.appendChild(style);
})();

function aplicarBlurDesenvolvimento(element) {
  if (!element || element.querySelector('.dev-blur-overlay')) return;

  element.classList.add('dev-blur-wrapper');

  const overlay = document.createElement('div');
  overlay.className = 'dev-blur-overlay';
  overlay.innerHTML = `
    <div class="dev-blur-msg">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      Ainda em desenvolvimento
    </div>
  `;

  element.appendChild(overlay);
}

// Aplica overlays após conteúdo dinâmico carregar
$(document).ajaxComplete(function () {
  setTimeout(function () {
    // 1. Gerenciar Modelos de Documentos
    const gridModelos = document.getElementById('gridDocsModelo');
    if (gridModelos && !gridModelos.parentElement.querySelector('.dev-blur-overlay')) {
      const parentModelos = gridModelos.closest('.section-card')
        || gridModelos.closest('.card')
        || gridModelos.parentElement;
      aplicarBlurDesenvolvimento(parentModelos);
    }

    // 2. Relatórios - info-card que contém botões de relatório
    const btnRelatorio = document.querySelector(
      '[onclick*="imprimir_rel"], [onclick*="modal_parametros"]'
    );
    if (btnRelatorio) {
      const cardRelatorio = btnRelatorio.closest('.info-card');
      if (cardRelatorio && !cardRelatorio.querySelector('.dev-blur-overlay')) {
        aplicarBlurDesenvolvimento(cardRelatorio);
      }
    }

    // 3. Inicializar lista dinâmica de alunos
    inicializarStudentList();
  }, 300);
});


// ============================================
// ALUNOS DINÂMICOS - Adicionar / Remover
// ============================================

var alunosLista = [];
var alunoContador = 0;
var studentListInicializado = false;

(function injetarEstilosAlunos() {
  var style = document.createElement('style');
  style.textContent = '\
    .student-rows-container {\
      display: flex;\
      flex-direction: column;\
      gap: 8px;\
    }\
    .student-row {\
      display: flex;\
      align-items: center;\
      gap: 10px;\
      padding: 8px 12px;\
      background: #f8fafc;\
      border: 1px solid #e2e8f0;\
      border-radius: 8px;\
      transition: all 0.2s ease;\
    }\
    .student-row:hover {\
      border-color: #cbd5e1;\
      background: #f1f5f9;\
    }\
    .student-row-number {\
      font-family: "DM Sans", sans-serif;\
      font-size: 12px;\
      font-weight: 700;\
      color: #94a3b8;\
      min-width: 20px;\
      text-align: center;\
    }\
    .student-row .student-field {\
      flex: 1;\
      padding: 6px 10px;\
      border: 1px solid #e2e8f0;\
      border-radius: 6px;\
      font-family: "DM Sans", sans-serif;\
      font-size: 13px;\
      color: #334155;\
      background: #fff;\
      transition: border-color 0.2s;\
    }\
    .student-row .student-field:focus {\
      outline: none;\
      border-color: #6366f1;\
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);\
    }\
    .student-row .student-field[readonly] {\
      background: #f1f5f9;\
      color: #64748b;\
      cursor: default;\
    }\
    .student-field-label {\
      font-family: "DM Sans", sans-serif;\
      font-size: 11px;\
      font-weight: 500;\
      color: #94a3b8;\
      min-width: 30px;\
    }\
    .btn-remove-student {\
      display: flex;\
      align-items: center;\
      justify-content: center;\
      width: 28px;\
      height: 28px;\
      border: none;\
      border-radius: 6px;\
      background: #fee2e2;\
      color: #ef4444;\
      cursor: pointer;\
      transition: all 0.2s;\
      flex-shrink: 0;\
    }\
    .btn-remove-student:hover {\
      background: #fecaca;\
      color: #dc2626;\
    }\
    .btn-add-student {\
      display: flex;\
      align-items: center;\
      gap: 6px;\
      margin-top: 8px;\
      padding: 6px 14px;\
      border: 1px dashed #cbd5e1;\
      border-radius: 8px;\
      background: transparent;\
      color: #64748b;\
      font-family: "DM Sans", sans-serif;\
      font-size: 13px;\
      font-weight: 500;\
      cursor: pointer;\
      transition: all 0.2s;\
    }\
    .btn-add-student:hover {\
      border-color: #6366f1;\
      color: #6366f1;\
      background: rgba(99, 102, 241, 0.04);\
    }\
    .student-row-fade-in {\
      animation: studentFadeIn 0.25s ease;\
    }\
    @keyframes studentFadeIn {\
      from { opacity: 0; transform: translateY(-8px); }\
      to { opacity: 1; transform: translateY(0); }\
    }\
  ';
  document.head.appendChild(style);
})();

/**
 * Inicializa o container .student-list com a estrutura dinâmica
 */
function inicializarStudentList() {
  var container = document.querySelector('.student-list');
  if (!container || studentListInicializado) return;
  studentListInicializado = true;

  container.innerHTML =
    '<div class="student-rows-container" id="student-rows"></div>' +
    '<button type="button" class="btn-add-student" onclick="adicionarAluno()">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">' +
        '<line x1="12" y1="5" x2="12" y2="19"></line>' +
        '<line x1="5" y1="12" x2="19" y2="12"></line>' +
      '</svg>' +
      'Adicionar aluno' +
    '</button>';
}

/**
 * Carrega alunos vindos do backend na lista dinâmica
 */
function carregarAlunosDinamicos(alunos) {
  inicializarStudentList();

  alunosLista = [];
  alunoContador = 0;
  var rowsContainer = document.getElementById('student-rows');
  if (rowsContainer) rowsContainer.innerHTML = '';

  alunos.forEach(function(aluno) {
    adicionarAluno(aluno.nome || '', aluno.ra || '');
  });
}

/**
 * Adiciona uma nova linha de aluno
 */
function adicionarAluno(nome, ra) {
  alunoContador++;
  var id = alunoContador;

  alunosLista.push({ id: id, nome: nome || '', ra: ra || '' });

  var rowsContainer = document.getElementById('student-rows');
  if (!rowsContainer) return;

  var idx = alunosLista.length;

  var row = document.createElement('div');
  row.className = 'student-row student-row-fade-in';
  row.id = 'student-row-' + id;
  row.setAttribute('data-student-id', id);

  row.innerHTML =
    '<span class="student-row-number">' + idx + '</span>' +
    '<span class="student-field-label">Nome</span>' +
    '<input type="text" class="student-field student-nome" ' +
      'id="student-nome-' + id + '" value="' + escapeAttr(nome || '') + '" ' +
      'placeholder="Nome do aluno" />' +
    '<span class="student-field-label">RA</span>' +
    '<input type="text" class="student-field student-ra" ' +
      'id="student-ra-' + id + '" value="' + escapeAttr(ra || '') + '" ' +
      'placeholder="RA" style="max-width: 120px;" />' +
    '<button type="button" class="btn-remove-student" onclick="removerAluno(' + id + ')" title="Remover aluno">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">' +
        '<line x1="18" y1="6" x2="6" y2="18"></line>' +
        '<line x1="6" y1="6" x2="18" y2="18"></line>' +
      '</svg>' +
    '</button>';

  rowsContainer.appendChild(row);

  row.querySelector('.student-nome').addEventListener('input', function() {
    atualizarDadoAluno(id, 'nome', this.value);
  });
  row.querySelector('.student-ra').addEventListener('input', function() {
    atualizarDadoAluno(id, 'ra', this.value);
  });
}

/**
 * Remove um aluno da lista
 */
function removerAluno(id) {
  alunosLista = alunosLista.filter(function(a) { return a.id !== id; });

  var row = document.getElementById('student-row-' + id);
  if (row) {
    row.style.transition = 'opacity 0.2s, transform 0.2s';
    row.style.opacity = '0';
    row.style.transform = 'translateY(-8px)';
    setTimeout(function() {
      row.remove();
      renumerarAlunos();
    }, 200);
  }

  sincronizarRAsGlobais();
}

/**
 * Renumera as linhas de alunos após remoção
 */
function renumerarAlunos() {
  var rows = document.querySelectorAll('#student-rows .student-row');
  rows.forEach(function(row, idx) {
    var numSpan = row.querySelector('.student-row-number');
    if (numSpan) numSpan.textContent = idx + 1;
  });
}

/**
 * Atualiza dados de um aluno no array
 */
function atualizarDadoAluno(id, campo, valor) {
  var aluno = alunosLista.find(function(a) { return a.id === id; });
  if (aluno) aluno[campo] = valor;
  sincronizarRAsGlobais();
}

/**
 * Sincroniza variáveis globais v_RA1/2/3 para compatibilidade
 */
function sincronizarRAsGlobais() {
  v_RA1 = alunosLista[0] ? alunosLista[0].ra : '';
  v_RA2 = alunosLista[1] ? alunosLista[1].ra : '';
  v_RA3 = alunosLista[2] ? alunosLista[2].ra : '';
}

/**
 * Retorna todos os RAs como string separada por vírgula
 */
function obterRAsAlunos() {
  return alunosLista
    .map(function(a) { return a.ra || ''; })
    .filter(function(ra) { return ra !== ''; })
    .join(',');
}

/**
 * Limpa a lista dinâmica de alunos
 */
function limparAlunosDinamicos() {
  alunosLista = [];
  alunoContador = 0;
  var rowsContainer = document.getElementById('student-rows');
  if (rowsContainer) rowsContainer.innerHTML = '';
  v_RA1 = ''; v_RA2 = ''; v_RA3 = '';
}

/**
 * Escapa atributos HTML
 */
function escapeAttr(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
