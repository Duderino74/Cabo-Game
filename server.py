from flask import Flask,request,jsonify,send_from_directory
import random,secrets,threading
app=Flask(__name__); rooms={}; lock=threading.RLock()
@app.route('/')
def index(): return send_from_directory('.', 'index.html')
@app.post('/api')
def api():
 with lock:
  try:return jsonify(act(request.json))
  except (ValueError,KeyError,IndexError) as e:return jsonify(error=str(e)),400

def act(d):
 a=d['action']; code=d.get('room','').upper(); token=d.get('token','')
 if a=='create':
  code=secrets.token_hex(3).upper();rooms[code]={'p':[],'phase':'lobby','scores':{}}
 r=rooms[code];p=r['p']
 if a in ('create','join'):
  if r['phase']!='lobby' or len(p)>=4:raise ValueError('Raum geschlossen oder voll')
  token=secrets.token_hex(16);p.append({'id':token,'name':str(d.get('name','Spieler'))[:24],'cards':[]});r['scores'][token]=0
 i=next((j for j,x in enumerate(p) if x['id']==token),-1)
 if i<0:raise ValueError('Bitte beitreten')
 me=p[i]
 if a=='start':
  if i!=0 or len(p)<2 or r['phase'] not in ('lobby','end'):raise ValueError('Start nicht möglich')
  deck=[0]*2+[v for v in range(1,13) for _ in range(4)]+[13]*2;random.shuffle(deck)
  for x in p:x['cards']=[deck.pop() for _ in range(4)]
  r.update(deck=deck,discard=[deck.pop()],phase='peek',turn=0,ready=[],caller=None,held=None,source=None,seen={},message='Merke dir deine ersten zwei Karten.')
 if a=='ready' and r['phase']=='peek':
  if i not in r['ready']:r['ready'].append(i)
  if len(r['ready'])==len(p):r['phase']='play'
 def finish():
  sums=[sum(x['cards']) for x in p]; c=r['caller']; low=min(sums)
  for j,x in enumerate(p):r['scores'][x['id']]+= (0 if sums[j]==low and (c is None or j==c) else sums[j]+(10 if j==c and sums[j]!=low else 0))
  r['phase']='end';r['message']='Runde beendet: '+', '.join(x['name']+': '+str(sums[j]) for j,x in enumerate(p))
 def advance():
  r['held']=None;r['seen']={};r['power']=None;r['turn']=(i+1)%len(p)
  if r['turn']==r['caller']:finish()
 if a in ('draw','take','swap','discard','cabo','power','skip'):
  if r['phase']!='play' or r['turn']!=i:raise ValueError('Nicht dein Zug')
  if a in ('draw','take'):
   if r['held'] is not None or r.get('power'):raise ValueError('Zug bereits begonnen')
   if a=='draw' and not r['deck']:
    r['deck']=r['discard'][:-1];r['discard']=r['discard'][-1:];random.shuffle(r['deck'])
   pile=r['deck'] if a=='draw' else r['discard'];r['held']=pile.pop();r['source']=a
  elif a=='cabo':
   if r['caller'] is not None or r['held'] is not None or r.get('power'):raise ValueError('CABO nicht möglich')
   r['caller']=i;r['message']=me['name']+' ruft CABO!';advance()
  elif a=='swap':
   if r['held'] is None:raise ValueError('Erst ziehen')
   k=int(d['card']);assert 0<=k<4
   r['discard'].append(me['cards'][k]);me['cards'][k]=r['held'];advance()
  elif a=='discard':
   if r['held'] is None or r['source']!='draw':raise ValueError('Nicht möglich')
   v=r['held'];r['discard'].append(v);r['held']=None
   if 7<=v<=12:r['power']='peek' if v<=8 else 'spy' if v<=10 else 'switch'
   else:advance()
  elif a=='power':
   power=r.get('power');j=int(d.get('player',i));k=int(d['card']);assert 0<=j<len(p) and 0<=k<4
   if power=='peek' and j==i or power=='spy' and j!=i:r['seen']={f'{j}:{k}':p[j]['cards'][k]};r['power']='done'
   elif power=='switch' and j!=i:
    own=int(d['own']);assert 0<=own<4
    me['cards'][own],p[j]['cards'][k]=p[j]['cards'][k],me['cards'][own];advance()
   else:raise ValueError('Aktion nicht möglich')
  elif a=='skip':
   if not r.get('power'):raise ValueError('Keine Sonderaktion')
   advance()
 phase=r['phase'];players=[]
 for j,x in enumerate(p):
  cards=[v if phase=='end' or (phase=='peek' and j==i and i not in r['ready'] and k<2) else r.get('seen',{}).get(f'{j}:{k}') if r.get('turn')==i else None for k,v in enumerate(x['cards'])]
  players.append({'name':x['name'],'cards':cards,'score':r['scores'][x['id']]})
 return dict(room=code,token=token,i=i,players=players,phase=phase,turn=r.get('turn'),held=r.get('held') if r.get('turn')==i else None,source=r.get('source'),power=r.get('power') if r.get('turn')==i else None,discard=r.get('discard',[None])[-1] if r.get('discard') else None,caller=r.get('caller'),message=r.get('message','Warte auf Mitspieler'),ready=i in r.get('ready',[]))
if __name__=='__main__':app.run(host='0.0.0.0',port=8000)
