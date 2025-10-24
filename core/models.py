from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
import random


class CustomUser(AbstractUser):
    TIPO_CHOICES = (
        ('admin', 'Admin'),
        ('professor', 'Professor'),
        ('aluno', 'Aluno'),
        ('servidor', 'Servidor'),
        ('diretor', 'Diretor'),
    )
    
    EIXO_CHOICES = (
        ('SAUDE', 'Eixo da Saúde'),
        ('GESTAO', 'Eixo de Gestão'),
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='admin')
    eixo = models.CharField(
        max_length=10, 
        choices=EIXO_CHOICES, 
        null=True, 
        blank=True, 
        help_text="Eixo ao qual o servidor pertence."
    )

    data_nascimento = models.DateField(null=True, blank=True)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    rg = models.CharField(max_length=12, unique=True, null=True, blank=True)
    orgao = models.CharField(max_length=10, null=True, blank=True)
    data_expedicao = models.DateField(null=True, blank=True)
    cidade_nascimento = models.CharField(max_length=100, null=True, blank=True)

    numero_matricula = models.CharField(max_length=20, unique=True, blank=True, null=True)

    nome_pai = models.CharField(max_length=150, blank=True, null=True)
    nome_mae = models.CharField(max_length=150, blank=True, null=True)
    responsavel_matricula = models.CharField(max_length=150, blank=True, null=True)

    endereco_rua = models.CharField(max_length=150, blank=True, null=True)
    endereco_numero = models.CharField(max_length=10, blank=True, null=True)
    endereco_bairro = models.CharField(max_length=100, blank=True, null=True)
    endereco_cidade = models.CharField(max_length=100, blank=True, null=True)
    endereco_cep = models.CharField(max_length=9, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)

    senha_temporaria = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.numero_matricula:
            ano = datetime.date.today().year
            if self.tipo == 'admin':
                self.numero_matricula = 'admin'
            else:
                aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(8)])
                self.numero_matricula = f"{ano}{aleatorio}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.tipo})"


class Curso(models.Model):
    EIXO_CHOICES = (
        ('SAUDE', 'Eixo da Saúde'),
        ('GESTAO', 'Eixo de Gestão'),
    )
    
    nome = models.CharField(max_length=100, unique=True)
    eixo = models.CharField(max_length=10, choices=EIXO_CHOICES, default='GESTAO')

    def __str__(self):
        return self.nome


class Turma(models.Model):
    ANO_MODULO_CHOICES = [
        ('1º ANO', '1º ANO'),
        ('2º ANO', '2º ANO'),
        ('3º ANO', '3º ANO'),
        ('I MÓDULO', 'I MÓDULO'),
        ('II MÓDULO', 'II MÓDULO'),
        ('III MÓDULO', 'III MÓDULO'),
        ('IV MÓDULO', 'IV MÓDULO'),
        ('V MÓDULO', 'V MÓDULO'),
        ('VI MÓDULO', 'VI MÓDULO'),
    ]

    TURNO_CHOICES = [
        ('matutino', 'Matutino'),
        ('vespertino', 'Vespertino'),
        ('noturno', 'Noturno'),
    ]

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    ano_modulo = models.CharField(max_length=20, choices=ANO_MODULO_CHOICES)
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES)
    turma = models.CharField(max_length=10, blank=True, null=True, help_text="Ex: M1, V2 ou deixe vazio se for módulo noturno.")
    modalidade = models.CharField(max_length=50, blank=True, null=True)
    sala = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('curso', 'ano_modulo', 'turno', 'turma', 'modalidade')

    def save(self, *args, **kwargs):
        if self.turno in ['matutino', 'vespertino']:
            self.modalidade = 'EPI'
        elif self.turno == 'noturno' and not self.modalidade:
            raise ValueError("Para turmas noturnas, a modalidade (Subsequente ou PROEJA) deve ser especificada.")
        super().save(*args, **kwargs)

    def __str__(self):
        turma_display = self.turma if self.turma else "-"
        return f"{self.ano_modulo} - {self.curso.nome} ({self.turno.upper()}) {turma_display} - {self.modalidade or ''}".strip()
    
    @property
    def nome_curto(self):
        """ Retorna um nome mais limpo para a turma (ex: M1, V1, ou o nome do módulo). """
        return self.turma or self.ano_modulo


class Materia(models.Model):
    nome = models.CharField(max_length=100)
    professores = models.ManyToManyField(CustomUser, limit_choices_to={'tipo': 'professor'}, blank=True)
    turmas = models.ManyToManyField(Turma, blank=True)
    ch = models.IntegerField(default=20)

    def __str__(self):
        return self.nome


class ProfessorMateriaAnoCursoModalidade(models.Model):
    MODALIDADE_CHOICES = [
        ('EPI', 'EPI'),
        ('PROEJA', 'PROEJA'),
        ('SUBSEQUENTE', 'Subsequente'),
    ]

    professor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'tipo': 'professor'})
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    ano_modulo = models.CharField(max_length=20, choices=Turma.ANO_MODULO_CHOICES)
    modalidade = models.CharField(max_length=20, choices=MODALIDADE_CHOICES)

    class Meta:
        unique_together = ('professor', 'materia', 'curso', 'ano_modulo', 'modalidade')
        verbose_name = "Vínculo de Professor"
        verbose_name_plural = "Vínculos de Professores"

    def __str__(self):
        return f"{self.professor.get_full_name()} - {self.materia.nome} ({self.curso.nome} - {self.ano_modulo} {self.modalidade})"


class AlunoTurma(models.Model):
    aluno = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'tipo': 'aluno'})
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    data_matricula = models.DateField(auto_now_add=True)
    ano_letivo = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        unique_together = ('aluno', 'turma')

    def save(self, *args, **kwargs):
        if not self.pk:
            hoje = datetime.date.today()
            semestre = 1 if hoje.month <= 6 else 2
            self.ano_letivo = f"{hoje.year}.{semestre}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.get_full_name()} - {self.turma}"


class Nota(models.Model):
    aluno = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'tipo': 'aluno'})
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)

    nota_1 = models.FloatField(null=True, blank=True)
    nota_2 = models.FloatField(null=True, blank=True)
    nota_3 = models.FloatField(null=True, blank=True)
    nota_recuperacao = models.FloatField(null=True, blank=True)
    media_final = models.FloatField(null=True, blank=True)
    status_final = models.CharField(max_length=30, blank=True)

    def calcular_media(self):
        notas = [self.nota_1, self.nota_2, self.nota_3]
        notas_validas = [n for n in notas if n is not None]
        if not notas_validas:
            return None
        return sum(notas_validas) / len(notas_validas)

    def calcular_status(self):
        media = self.calcular_media()
        if media is None:
            return "Pendente"
        if media >= 5:
            return "Aprovado"
        elif self.nota_recuperacao is not None:
            final = (media + self.nota_recuperacao) / 2
            return "Aprovado" if final >= 5 else "Reprovado na Final"
        else:
            return "Reprovado"

    def save(self, *args, **kwargs):
        self.media_final = self.calcular_media()
        self.status_final = self.calcular_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.get_full_name()} - {self.materia.nome} - {self.status_final}"


class Estagio(models.Model):
    aluno = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'tipo': 'aluno'})
    orientador = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='estagios_orientados', limit_choices_to={'tipo': 'professor'})
    
    supervisor_nome = models.CharField(max_length=150)
    supervisor_empresa = models.CharField(max_length=150)
    supervisor_cargo = models.CharField(max_length=100)
    supervisor_email = models.EmailField(blank=True, null=True)
    
    data_inicio = models.DateField()
    data_fim = models.DateField()
    status_geral = models.CharField(max_length=50, default="Em andamento")

    def __str__(self):
        return f"Estágio de {self.aluno.get_full_name()}"


class DocumentoEstagio(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('AVALIACAO_ORIENTADOR', 'Avaliação do Orientador'),
        ('AVALIACAO_SUPERVISOR', 'Avaliação do Supervisor'),
        ('TERMO_COMPROMISSO', 'Termo de Compromisso'),
        ('FICHA_IDENTIFICACAO', 'Ficha de Identificação'),
        ('FICHA_PESSOAL', 'Ficha Pessoal'),
        ('COMP_RESIDENCIA', 'Comprovante de Residência'),
        ('COMP_AGUA_LUZ', 'Comprovante de Água/Luz'),
        ('ID_CARD', 'Cartão de Identidade'),
        ('SUS_CARD', 'Cartão do SUS'),
        ('VACINA_CARD', 'Cartão de Vacina'),
        ('APOLICE_SEGURO', 'Apólice de Seguro'),
    ]

    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho (em preenchimento pelo aluno)'),
        ('AGUARDANDO_ASSINATURAS', 'Aguardando Assinaturas'),
        ('EM_VERIFICACAO', 'Em Verificação (pelo Servidor)'),
        ('FINALIZADO', 'Finalizado e Arquivado'),
    ]

    estagio = models.ForeignKey(Estagio, on_delete=models.CASCADE, related_name='documentos')
    tipo_documento = models.CharField(max_length=50, choices=TIPO_DOCUMENTO_CHOICES)
    
    dados_formulario = models.JSONField(default=dict, blank=True, help_text="Respostas do formulário preenchido pelo usuário.")
    
    arquivo_anexo = models.FileField(upload_to='anexos_estagio/', blank=True, null=True)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RASCUNHO')

    assinado_aluno_em = models.DateTimeField(null=True, blank=True)
    assinado_orientador_em = models.DateTimeField(null=True, blank=True)
    assinado_diretor_em = models.DateTimeField(null=True, blank=True)
    
    pdf_supervisor_assinado = models.FileField(upload_to='pdfs_assinados/', blank=True, null=True)

    publico = models.BooleanField(default=False, help_text="Se marcado, o orientador e servidor podem ver.")
    data_upload = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('estagio', 'tipo_documento')

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.estagio.aluno.get_full_name()}"