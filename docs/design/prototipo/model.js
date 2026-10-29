/* Cálculos de apresentação para o protótipo. Não é um motor analítico de produção. */
(function(root){
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function validDate(value) {
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value||''))return false;
    const date=new Date(value+'T12:00:00Z');
    return !Number.isNaN(date.valueOf())&&date.toISOString().slice(0,10)===value;
  }
  function filterDraws(game, filter={}) {
    const selected=game.draws.filter(d=>(!filter.from||d.date>=filter.from)&&(!filter.to||d.date<=filter.to));
    return filter.limit?selected.slice(-Number(filter.limit)):selected;
  }
  function describe(draws,maximum,component='main') {
    const frequencies=Array.from({length:maximum},(_,i)=>({number:i+1,count:0,gap:null}));
    draws.forEach((draw,index)=>(draw[component]||[]).forEach(n=>{frequencies[n-1].count++;frequencies[n-1].gap=draws.length-index-1;}));
    const sums=draws.map(d=>({date:d.date,id:d.id,value:d.main.reduce((a,b)=>a+b,0)}));
    const evenCounts=draws.map(d=>d.main.filter(n=>n%2===0).length);
    return {count:draws.length,frequencies,ranked:[...frequencies].sort((a,b)=>b.count-a.count||a.number-b.number),sums,
      averageSum:draws.length?sums.reduce((a,b)=>a+b.value,0)/draws.length:null,
      averageEven:draws.length?evenCounts.reduce((a,b)=>a+b,0)/draws.length:null,
      evenCounts};
  }
  function validateDraft(value,existing) {
    if(!value.name.trim())return 'Informe o nome da modalidade.';
    if(!/^[a-z][a-z0-9_]{2,39}$/.test(value.slug))return 'Use um identificador de 3 a 40 caracteres: letras minúsculas, números e sublinhado.';
    if(existing.some(g=>g.slug===value.slug))return 'Esse identificador já está cadastrado. Escolha outro.';
    if(!Number.isInteger(value.count)||!Number.isInteger(value.maximum)||value.count<1||value.maximum<value.count||value.maximum>100)return 'A quantidade principal deve ser inteira e ficar entre 1 e o limite, de no máximo 100.';
    if(!Number.isInteger(value.specialCount)||!Number.isInteger(value.specialMaximum)||value.specialCount<0||value.specialCount>value.specialMaximum||value.specialMaximum>100)return 'Revise a quantidade e o limite dos números especiais.';
    if(value.specialCount&&!value.specialLabel.trim())return 'Dê um nome ao componente especial.';
    if(!/^[A-Z]{3}$/.test(value.currency))return 'Selecione uma moeda válida.';
    return null;
  }
  const api={escape,validDate,filterDraws,describe,validateDraft};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.LottoUIModel=api;
})(typeof window!=='undefined'?window:globalThis);
