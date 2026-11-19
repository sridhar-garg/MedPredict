(function (root) {
  'use strict';
  function sigmoid(z) { return z > 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z)); }
  function dist(a,b) { let total=0; for(let i=0;i<a.length;i++) total+=(a[i]-b[i])**2; return total; }
  function dot(a,b) { let total=0; for(let i=0;i<a.length;i++) total+=a[i]*b[i]; return total; }
  function coupledProbability(decision, A, B) {
    // Binary LIBSVM probability calibration, including pairwise coupling.
    const r01=Math.min(Math.max(sigmoid(A*decision-B),1e-7),1-1e-7), r10=1-r01;
    const Q=[[r10*r10,-r10*r01],[-r10*r01,r01*r01]], p=[.5,.5];
    for(let i=0;i<100;i++) {
      let qp=Q.map(row=>dot(row,p)), pqp=dot(p,qp);
      if(Math.max(...qp.map(v=>Math.abs(v-pqp)))<.0025) break;
      for(let j=0;j<2;j++) {
        const diff=(-qp[j]+pqp)/Q[j][j]; p[j]+=diff;
        pqp=(pqp+diff*(diff*Q[j][j]+2*qp[j]))/((1+diff)**2);
        for(let k=0;k<2;k++){ qp[k]=(qp[k]+diff*Q[j][k])/(1+diff); p[k]/=1+diff; }
      }
    }
    return p[1];
  }
  function probability(m, row) {
    if(row.length!==m.mean.length) throw Error('Wrong feature count');
    const x=row.map((v,i)=>(Number.isFinite(v)?v:m.impute[i])-m.mean[i]).map((v,i)=>v/m.scale[i]);
    switch(m.type) {
      case 'linear': return sigmoid(dot(m.coef,x)+m.intercept);
      case 'svm': {
        const d=m.support.reduce((v,s,i)=>v+m.coef[i]*Math.exp(-m.gamma*dist(s,x)),m.intercept);
        return coupledProbability(d,m.probA,m.probB);
      }
      case 'knn': {
        const nearest=m.samples.map((s,i)=>[dist(x,s),i]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]).slice(0,m.k);
        return nearest.reduce((total,p)=>total+m.labels[p[1]],0)/m.k;
      }
      case 'forest': {
        const xx=x.map(Math.fround);
        return m.trees.reduce((total,t)=>{let n=0; while(t[2][n]!==-1) n=xx[t[0][n]]<=t[1][n]?t[2][n]:t[3][n]; return total+t[4][n];},0)/m.trees.length;
      }
      case 'xgb': {
        const xx=x.map(Math.fround); let total=Math.fround(Math.log(m.base/(1-m.base)));
        for(let t of m.trees){while(t.length!==1)t=xx[t[0]]<Math.fround(t[1])?t[2]:t[3];total=Math.fround(total+Math.fround(t[0]));}
        return sigmoid(total);
      }
      default: throw Error('Unknown model type');
    }
  }
  function predict(spec,row) {
    const values=Object.entries(spec.models).map(([name,m])=>({name,probability:probability(m,row)}));
    if(values.some(v=>!Number.isFinite(v.probability)||v.probability<0||v.probability>1))throw Error('Invalid model estimate');
    return {models:values,mean:values.reduce((x,p)=>x+p.probability,0)/values.length};
  }
  const api={probability,predict};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MPModels=api;
})(typeof globalThis==='undefined'?this:globalThis);
