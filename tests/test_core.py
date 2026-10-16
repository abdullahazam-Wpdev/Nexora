import torch
import pytest
from nexora.model import Core,Config
from nexora.datasets import prepare

torch.set_num_threads(2)
def test_shape_causality_and_gradients():
    torch.manual_seed(1)
    model=Core(Config(vocab_size=32,dim=32,layers=1,heads=4,context=16))
    x=torch.randint(0,32,(2,12)); altered=x.clone();altered[:,7:]=torch.randint(0,32,(2,5))
    y=model(x)
    assert y.shape==(2,12,32)
    torch.testing.assert_close(y[:,:7],model(altered)[:,:7],atol=1e-6,rtol=1e-5)
    y.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())

def test_tiny_batch_overfit():
    torch.manual_seed(2)
    m=Core(Config(vocab_size=16,dim=32,layers=1,heads=4,context=16))
    x=torch.tensor([[1,2,3,4,5,6,7,8]]);y=(x+1)%16
    opt=torch.optim.AdamW(m.parameters(),lr=.015)
    values=[]
    for _ in range(70):
        opt.zero_grad();loss=torch.nn.functional.cross_entropy(m(x).flatten(0,1),y.flatten());values.append(loss.item());loss.backward();opt.step()
    assert values[-1]<.05
    assert values[-1]<values[0]*.05

def test_data_approval_secrets_and_splits():
    texts=[f'Unique arithmetic document number {i}.' for i in range(20)]
    with pytest.raises(ValueError):prepare(texts,approved=False,license='CC0-1.0',provenance='test')
    with pytest.raises(ValueError):prepare(texts+['api_key=do-not-ingest-this-secret'],approved=True,license='CC0-1.0',provenance='test')
    d=prepare(texts+texts,approved=True,license='CC0-1.0',provenance='test')
    assert d['documents']==20
    a,b,c=map(set,d['splits'].values())
    assert not(a&b or a&c or b&c)

def test_checkpoint_roundtrip_and_generate(tmp_path):
    from safetensors.torch import save_file,load_file
    c=Config(vocab_size=32,dim=32,layers=1,heads=4,context=16)
    m=Core(c); x=torch.tensor([[1,2,3]])
    save_file(m.state_dict(),str(tmp_path/'model.safetensors'))
    n=Core(c);n.load_state_dict(load_file(str(tmp_path/'model.safetensors')))
    torch.testing.assert_close(m(x),n(x))
    assert n.generate(x,5).shape==(1,8)

def test_training_tokenizer_and_resume(tmp_path,monkeypatch):
    import json
    from tokenizers import Tokenizer
    import nexora.train as training
    monkeypatch.setattr(training,'STORE',tmp_path)
    first=training.run(3)
    tokenizer=Tokenizer.from_file(str(tmp_path/'tiny-core/tokenizer.json'))
    text='2 + 3 = 5. café'
    assert tokenizer.decode(tokenizer.encode(text).ids)==text
    resumed=training.run(2,resume=True)
    assert first['steps']==3 and resumed['steps']==5
    assert resumed['history'][:len(first['history'])]==first['history']
    assert (tmp_path/'tiny-core/model.safetensors').exists()
    assert training.infer('2 + 3 =',4)['new_tokens']==4
