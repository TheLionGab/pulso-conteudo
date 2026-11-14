import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('pipeline', Path(__file__).with_name('pulso_news_app.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ep = Path(self.tmp.name)
        self.meta = {'id':'pulso-news-2026-11-14-diesel','publicado_em':'2026-11-14',
                     'titulo':"Diesel d'água",'resumo':'Não é reajuste','duracao_seg':43,
                     'culturas':[],'push_titulo':'Diesel','push_corpo':'Confira a cotação',
                     'fontes':[{'nome':'ANP','data':'2026-11-10','url':'https://www.gov.br/anp'}]}
        self.write('out/meta-app.json', self.meta)
        for name, data in [('out/video.mp4',b'video'),('out/capa.jpg',b'capa'),('qa/prova.json',b'prova')]:
            p = self.ep/name; p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.sha = app.wf.digest(self.ep/'out/video.mp4')
        self.manifest = {'video':{'arquivo':'out/video.mp4','sha256':self.sha,'bytes':5},
                         'capa':{'arquivo':'out/capa.jpg','sha256':app.wf.digest(self.ep/'out/capa.jpg'),'bytes':4},
                         'entradas_sha256':{}}
        self.write('out/manifesto.json',self.manifest)
        (self.ep/'qa/recibo-critico-publicacao.txt').write_text('APROVADO SHA256 '+self.sha)
        self.ready = {'video_sha256':self.sha,'gates':{g:{'resultado':'aprovado','evidencias':[
                      {'arquivo':'qa/prova.json','sha256':app.wf.digest(self.ep/'qa/prova.json')}]} for g in app.GATES}}
        self.write('out/pronto-app.json',self.ready)

    def write(self, name, data):
        app.atomic(self.ep,name,data)

    def plan(self):
        plan,sql=app.prepare(self.ep,[])
        self.write('out/plano-app.json',plan)
        (self.ep/'qa/publicar-app.sql').write_text(sql)
        self.write('qa/revisao-sql.json',{'aprovado':True,'sql_sha256':plan['sql_sha256']})
        return plan

    def auth(self):
        self.write('qa/autorizacao.json',{'confirmacao_inequivoca_da_dispensa':True,'id':self.meta['id'],
                   'video_sha256':self.sha,'reutilizavel':False,'motivo':'Exceção expressa do dono desta edição'})

    def test_prepare_e_local_e_sql_escapa_texto_sem_deletar(self):
        with patch.object(app,'cli',side_effect=AssertionError('rede proibida')):
            plan,sql=app.prepare(self.ep,[])
        self.assertIn("Diesel d''água",sql)
        self.assertNotIn('DELETE',sql)
        self.assertEqual(plan['project'],app.PROJECT)
        self.assertIn(self.sha[:12],plan['video_path'])

    def test_dia_ocupado_nao_se_substitui_implicitamente(self):
        old={'id':'pulso-news-2026-11-14','publicado_em':'2026-11-14','status':'publicado'}
        with self.assertRaises(ValueError):app.prepare(self.ep,[old])
        plan,sql=app.prepare(self.ep,[old],old['id'])
        self.assertEqual(plan['previous'],old)
        self.assertIn('FOR UPDATE',sql)
        self.assertIn('to_jsonb(e)',sql)
        self.assertIn("status='rascunho'",sql)

    def test_gate_reprovado_incompleto_ou_prova_alterada_bloqueia(self):
        self.ready['gates']['G0']['resultado']='reprovado';self.write('out/pronto-app.json',self.ready)
        with self.assertRaises(ValueError):app.candidate(self.ep)

    def test_snapshot_tem_timestamps_normalizados_pelo_tipo_postgres(self):
        old={'id':'pulso-news-2026-11-14','publicado_em':'2026-11-14','status':'publicado',
             'aprovado_em':'2026-11-14 14:23:18.552+00'}
        _,sql=app.prepare(self.ep,[old],old['id'])
        self.assertIn('to_jsonb(e)=to_jsonb(jsonb_populate_record(NULL::public.pulso_news_episodios,',sql)
        self.assertIn('2026-11-14 14:23:18.552+00',sql)
        self.ready['gates']['G0']['resultado']='aprovado';self.write('out/pronto-app.json',self.ready)
        (self.ep/'qa/prova.json').write_text('prova alterada')
        with self.assertRaises(ValueError):app.candidate(self.ep)

    def test_midia_alterada_bloqueia(self):
        (self.ep/'out/video.mp4').write_bytes(b'outro')
        with self.assertRaises(ValueError):app.candidate(self.ep)

    def test_delimitador_do_nao_pode_ser_encerrado_por_metadados(self):
        meta=dict(self.meta,titulo="notícia $publicacao$; SELECT 'x'; --")
        old={'id':'pulso-news-2026-11-14','publicado_em':'2026-11-14','status':'publicado',
             'titulo':'snapshot $publicacao$ END; --'}
        sql=app.sql_for(meta,{'video_path':'a/video.mp4','capa_path':'a/capa.jpg'},old)
        tag=sql.split('BEGIN',1)[0][3:]
        self.assertTrue(tag.startswith('$pulso_'))
        self.assertEqual(sql.count(tag),2)
        self.assertIn('$publicacao$',sql)
        # Também protege um dado que tente usar a primeira tag derivada.
        meta['resumo']=tag
        revised=app.sql_for(meta,{'video_path':'a/video.mp4','capa_path':'a/capa.jpg'},old)
        next_tag=revised.split('BEGIN',1)[0][3:]
        self.assertNotEqual(tag,next_tag)
        self.assertEqual(revised.count(next_tag),2)

    def test_symlink_saida_e_escape_recusados(self):
        (self.ep/'fora').symlink_to(Path(self.tmp.name).parent,target_is_directory=True)
        for name in ('../arquivo.json','fora/arquivo.json','/tmp/arquivo.json'):
            with self.subTest(name=name),self.assertRaises(ValueError):self.write(name,{})

    def test_sql_sem_revisao_ou_de_outro_plano_nao_executa(self):
        plan=self.plan();self.auth()
        for mutation in ('review','sql','paths'):
            with self.subTest(mutation=mutation):
                if mutation=='review':self.write('qa/revisao-sql.json',{'aprovado':False})
                elif mutation=='sql':(self.ep/'qa/publicar-app.sql').write_text('select 1;')
                else:plan['video_path']='f'*32+'/video-'+self.sha[:12]+'.mp4'
                with patch.object(app,'cli',side_effect=AssertionError('não pode chegar à rede')):
                    with self.assertRaises(ValueError):app.publish(self.ep,plan,Path('/publisher.mjs'),'qa/autorizacao.json')
                plan=self.plan()

    def test_excecao_g6_de_outro_video_nao_libera(self):
        plan=self.plan();self.auth();a=app.load(self.ep,'qa/autorizacao.json');a['video_sha256']='0'*64
        self.write('qa/autorizacao.json',a)
        with patch.object(app,'cli',side_effect=AssertionError('sem rede')):
            with self.assertRaises(ValueError):app.publish(self.ep,plan,Path('/publisher.mjs'),'qa/autorizacao.json')

    def test_g6_vermelho_nao_gera_journal_upload_ou_sql(self):
        plan=self.plan();(self.ep/'dossie.json').write_text('{}')
        with patch.object(app.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaises(ValueError):app.publish(self.ep,plan,Path('/publisher.mjs'))
            self.assertEqual(run.call_count,1)
        self.assertFalse((self.ep/'out/publicacao/estado.json').exists())

    def test_tentativa_incerta_nao_reenvia(self):
        plan=self.plan();self.auth()
        self.write('out/publicacao/estado.json',{'video_sha256':self.sha,'app':{'phase':'uncertain'}})
        with patch.object(app.subprocess,'run',side_effect=AssertionError('sem mutação')):
            with self.assertRaises(ValueError):app.publish(self.ep,plan,Path('/publisher.mjs'),'qa/autorizacao.json')

    def test_falha_apos_upload_marca_incerto_e_preserva_instagram(self):
        plan=self.plan();self.auth()
        self.write('out/publicacao/estado.json',{'video_sha256':self.sha,'instagram':{'phase':'verified'}})
        cols=[{'column_name':k} for k in self.meta]
        with patch.object(app,'cli',side_effect=[cols,[]]),patch.object(app.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaises(RuntimeError):app.publish(self.ep,plan,Path('/publisher.mjs'),'qa/autorizacao.json')
            self.assertEqual(run.call_count,1)
        journal=app.load(self.ep,'out/publicacao/estado.json')
        self.assertEqual(journal['app']['phase'],'uncertain')
        self.assertEqual(journal['instagram']['phase'],'verified')
        self.assertTrue((self.ep/'qa/backup-app-antes-publicacao.json').exists())

    def test_sucesso_exige_anon_e_midias_e_preserva_recibo_instagram(self):
        plan=self.plan();self.auth()
        self.write('out/publicado.json',{'video_sha256':self.sha,'reel':'https://www.instagram.com/pulsodocampo/reel/test/','conta':'pulsodocampo'})
        row={'id':self.meta['id'],'status':'publicado','video_path':plan['video_path'],
             'capa_path':plan['capa_path'],'aprovado_em':'2026-11-14T20:00:00Z'}
        with patch.object(app,'cli',side_effect=[[{'column_name':k} for k in self.meta],[],[row]]),\
             patch.object(app.subprocess,'run') as run,patch.object(app,'public_media') as media:
            run.return_value.returncode=0
            result=app.publish(self.ep,plan,Path('/publisher.mjs'),'qa/autorizacao.json')
        self.assertEqual(result['status'],'publicado')
        self.assertEqual(media.call_count,2)
        self.assertEqual(app.load(self.ep,'out/publicado.json')['conta'],'pulsodocampo')
        self.assertEqual(app.load(self.ep,'out/publicacao/estado.json')['app']['phase'],'verified')


if __name__=='__main__':unittest.main()
