var DownloadResultados = (function () {
    const downloadResultados = {};

    const baixarDocumento = function (modalidade) {
        if (modalidade) {
            LoteriasCaixa.obterParametro().then(function () {
                let url = LoteriasCaixa.parametroUrlApi + '/api/resultados/download?modalidade=' + modalidade;
                $("#loading").show();

                $.ajax({
                    type: "GET",
                    url: url,
                    xhrFields: {
                        responseType: 'blob'
                    },
                    success: function (result) {
                        let link = document.createElement('a');
                        link.href = window.URL.createObjectURL(result);
                        link.download = modalidade + '.xlsx';
                        link.click();
                        $("#loading").hide();
                    },
                    error: function (erro) {
                        console.log(erro);
                        $("#loading").hide();
                    }
                });
            });
        }
    }

    const montarDownloadResultados = function (dados, modalidade) {
        if (dados.paragrafoDownloadResultados) {
            let htmlParagrafo = '<p dir = "ltr">';
            htmlParagrafo += dados.paragrafoDownloadResultados;
            htmlParagrafo += '</p>';

            jQuery('#textosdownload').append(htmlParagrafo);
        }

        let htmlBotaoResultados = '<button type="button" class="submit-d submit-white submit-small submit-non-fluid" id="btnResultados" title="';
        htmlBotaoResultados += dados.descricaoBotaoDownloadResultados;
        htmlBotaoResultados += '">';
        htmlBotaoResultados += dados.textoBotaoDownloadResultados;
        htmlBotaoResultados += '</button>';

        jQuery('#textosdownload').append(htmlBotaoResultados);

        jQuery("#btnResultados").click(function (e) {
            e.stopPropagation();
            e.preventDefault();
            baixarDocumento(modalidade);
        });
    }

    const obterDados = function () {
        let modalidade = document.getElementById('tituloModalidade').innerHTML.trim().replace("Super Sete", "Super 7");
        LoteriasCaixa.obterParametro().then(function () {
            jQuery.ajax({
                url: LoteriasCaixa.parametroUrlApi + "/api/loterias/textos-download-resultados?modalidade=" + modalidade,
                method: "GET"
            }).done(function (data) {
                montarDownloadResultados(data, modalidade);
            }).fail(function (error) {
                console.log("Erro ao obter textos download resultados.");
            });
        });
    }

    downloadResultados.iniciar = function () {
        obterDados();
    };

    return downloadResultados;
})();

_spBodyOnLoadFunctionNames.push("DownloadResultados.iniciar");