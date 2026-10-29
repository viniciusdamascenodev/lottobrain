LoteriasCaixa = (function () {
    'use strict'

    const loteriasCaixa = {};
    loteriasCaixa.parametroUrlApi = undefined;

    loteriasCaixa.obterParametro = function () {
        if (!loteriasCaixa.parametroUrlApi) {
            let deferred = jQuery.Deferred();

            jQuery.ajax({
                url: "/Style Library/json/params.txt",
                method: "GET"
            }).done(function (data) {
                loteriasCaixa.parametroUrlApi = JSON.parse(data).urlapiloterias;
                deferred.resolve(loteriasCaixa.parametroUrlApi);
            }).fail(function (error) {
                loteriasCaixa.parametroUrlApi = error;
                deferred.reject(error);
            });

            loteriasCaixa.parametroUrlApi = deferred.promise();
        }

        return jQuery.when(loteriasCaixa.parametroUrlApi);
    };

    loteriasCaixa.obterValorDoParametroDaUrl = function (parametro) {
        parametro = parametro.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        const regex = new RegExp('[\\?&]' + parametro + '=([^&#]*)');
        const parametros = regex.exec(location.search);
        return parametros === null ? '' : decodeURIComponent(parametros[1].replace(/\+/g, ' '));
    };

    return loteriasCaixa;
})();