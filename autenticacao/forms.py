from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
from django.forms import modelformset_factory, BaseModelFormSet
from core.models import Turma, AlunoTurma, ProfessorMateriaAnoCursoModalidade, Curso, Estagio
import datetime
import random

CustomUser = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={'autofocus': True, 'name': 'username', 'class': 'form-control'})
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
        return self.cleaned_data
    
class ProfessorMateriaAnoCursoModalidadeForm(forms.ModelForm):
    class Meta:
        model = ProfessorMateriaAnoCursoModalidade
        fields = ['materia', 'curso', 'ano_modulo', 'modalidade']
        labels = {
            'materia': 'Matéria',
            'curso': 'Curso',
            'ano_modulo': 'Ano/Módulo',
            'modalidade': 'Modalidade',
        }
        widgets = {
            'materia': forms.Select(attrs={'class': 'form-select'}),
            'curso': forms.Select(attrs={'class': 'form-select'}),
            'ano_modulo': forms.Select(attrs={'class': 'form-select'}),
            'modalidade': forms.Select(attrs={'class': 'form-select'}),
        }

class RequiredIdFormSet(BaseModelFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if 'id' in form.fields:
            form.fields['id'].required = False

ProfessorMateriaAnoCursoModalidadeFormSet = modelformset_factory(
    ProfessorMateriaAnoCursoModalidade,
    form=ProfessorMateriaAnoCursoModalidadeForm,
    extra=3,
    can_delete=True,
    formset=RequiredIdFormSet
)

class AlunoCreateForm(forms.ModelForm):
    curso = forms.ModelChoiceField(
        queryset=Curso.objects.all().order_by('nome'),
        label="1. Escolha o Curso",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ano_modulo = forms.ChoiceField(
        label="2. Escolha o Ano/Módulo",
        choices=[('', '---------')], 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    turno = forms.ChoiceField(
        label="3. Escolha o Turno",
        choices=[('', '---------')], 
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.none(), 
        label="4. Escolha a Turma",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name',
            'data_nascimento', 'cidade_nascimento',
            'rg', 'orgao', 'data_expedicao', 'cpf',
            'nome_pai', 'nome_mae', 'responsavel_matricula',
            'endereco_rua', 'endereco_numero', 'endereco_bairro',
            'endereco_cidade', 'endereco_cep', 'telefone', 'email',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define que o texto exibido no dropdown 'turma' será o nome curto
        self.fields['turma'].label_from_instance = lambda obj: obj.nome_curto

        # Lógica para repopular os 'choices' quando um formulário com erros é submetido (POST)
        if 'curso' in self.data:
            try:
                curso_id = int(self.data.get('curso'))
                self.fields['ano_modulo'].choices = [('', '---------')] + list(Turma.objects.filter(curso_id=curso_id).order_by('ano_modulo').values_list('ano_modulo', 'ano_modulo').distinct())
                
                if 'ano_modulo' in self.data:
                    ano_modulo_val = self.data.get('ano_modulo')
                    self.fields['turno'].choices = [('', '---------')] + list(Turma.objects.filter(curso_id=curso_id, ano_modulo=ano_modulo_val).values_list('turno', 'turno').distinct())
                    
                    if 'turno' in self.data:
                        turno_val = self.data.get('turno')
                        self.fields['turma'].queryset = Turma.objects.filter(curso_id=curso_id, ano_modulo=ano_modulo_val, turno=turno_val).order_by('turma')
            except (ValueError, TypeError):
                pass  # Ignora erros se os dados forem inválidos
        # Lógica para preencher os campos na tela de EDIÇÃO (GET)
        if self.instance and self.instance.pk:
            try:
                turma_atual = self.instance.alunoturma_set.first().turma
                if turma_atual:
                    self.fields['curso'].initial = turma_atual.curso
                    
                    anos_queryset = Turma.objects.filter(curso=turma_atual.curso).values_list('ano_modulo', 'ano_modulo').distinct()
                    self.fields['ano_modulo'].choices = [('', '---------')] + list(anos_queryset)
                    self.fields['ano_modulo'].initial = turma_atual.ano_modulo
                    
                    turnos_queryset = Turma.objects.filter(curso=turma_atual.curso, ano_modulo=turma_atual.ano_modulo).values_list('turno', flat=True).distinct()
                    self.fields['turno'].choices = [('', '---------')] + [(v, d) for v, d in Turma.TURNO_CHOICES if v in turnos_queryset]
                    self.fields['turno'].initial = turma_atual.turno
                    
                    self.fields['turma'].queryset = Turma.objects.filter(pk=turma_atual.pk)
                    self.fields['turma'].initial = turma_atual
            except (AttributeError, Exception):
                pass

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        return ''.join(filter(str.isdigit, cpf))

    def clean_rg(self):
        rg = self.cleaned_data.get('rg', '')
        return ''.join(filter(str.isdigit, rg))

    def save(self, commit=True):
        aluno = super().save(commit=False)
        aluno.tipo = 'aluno'
        
        if not aluno.pk:
            ano = datetime.date.today().year
            aleatorio = ''.join(str(random.randint(0, 9)) for _ in range(8))
            aluno.numero_matricula = f"{ano}{aleatorio}"
            aluno.username = aluno.numero_matricula
            aluno.set_password("Senha123#")
            aluno.senha_temporaria = True

        if commit:
            aluno.save()
            turma_selecionada = self.cleaned_data.get('turma')
            if turma_selecionada:
                AlunoTurma.objects.update_or_create(
                    aluno=aluno,
                    defaults={'turma': turma_selecionada}
                )
        return aluno


class ProfessorCreateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name',
            'data_nascimento',          
            'cidade_nascimento',
            'rg',
            'orgao',
            'data_expedicao',
            'cpf',
            'nome_pai',
            'nome_mae',
            'endereco_rua',
            'endereco_numero',
            'endereco_bairro',
            'endereco_cidade',
            'endereco_cep',
            'telefone',
        ]

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        return ''.join(filter(str.isdigit, cpf))

    def clean_rg(self):
        rg = self.cleaned_data.get('rg', '')
        return ''.join(filter(str.isdigit, rg))

    def save(self, commit=True):
        professor = super().save(commit=False)
        professor.tipo = 'professor'
        ano = datetime.date.today().year
        aleatorio = ''.join(str(random.randint(0, 9)) for _ in range(8))
        professor.numero_matricula = f"{ano}{aleatorio}"
        professor.username = professor.numero_matricula
        professor.set_password("Senha123#")
        professor.senha_temporaria = True

        if commit:
            professor.save()
        return professor


class ServidorCreateForm(forms.ModelForm):
    TIPO_USUARIO_CHOICES = (
        ('', '---------'),
        ('servidor', 'Administrativo'),
        ('direcao', 'Direção'),
    )
    tipo_usuario = forms.ChoiceField(
        choices=TIPO_USUARIO_CHOICES,
        label="Tipo de Usuário",
        required=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'eixo',
            'data_nascimento', 'cidade_nascimento', 'cpf', 'rg', 'orgao', 'data_expedicao',
            'nome_mae', 'nome_pai',
            'telefone', 'endereco_cep', 'endereco_cidade', 'endereco_bairro', 'endereco_rua', 'endereco_numero',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'eixo' in self.fields:
            self.fields['eixo'].required = False
        
        field_order = ['tipo_usuario', 'eixo', 'first_name', 'last_name', 'email', 'cpf', 'rg']
        self.order_fields(field_order)

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        return ''.join(filter(str.isdigit, cpf))

    def clean_rg(self):
        rg = self.cleaned_data.get('rg', '')
        return ''.join(filter(str.isdigit, rg))

    def save(self, commit=True):
        servidor = super().save(commit=False)
        
        ano = datetime.date.today().year
        aleatorio = ''.join(str(random.randint(0, 9)) for _ in range(8))
        servidor.numero_matricula = f"{ano}{aleatorio}"
        servidor.username = servidor.numero_matricula
        servidor.set_password("Senha123#")
        servidor.senha_temporaria = True

        if commit:
            servidor.save()
        return servidor
    
class EstagioCreateForm(forms.ModelForm):
    """
    Formulário para o Aluno solicitar a abertura do seu
    processo de estágio, preenchendo os dados iniciais.
    """
    class Meta:
        model = Estagio
        
        # Campos que o aluno deve preencher
        fields = [
            'supervisor_nome', 
            'supervisor_empresa', 
            'supervisor_cargo', 
            'supervisor_email', 
            'data_inicio', 
            'data_fim'
        ]
        
        # Labels (textos) que aparecerão no formulário
        labels = {
            'supervisor_nome': 'Nome do Supervisor da Empresa',
            'supervisor_empresa': 'Nome da Empresa Concedente',
            'supervisor_cargo': 'Cargo do Supervisor',
            'supervisor_email': 'Email do Supervisor',
            'data_inicio': 'Data de Início Prevista',
            'data_fim': 'Data de Término Prevista',
        }
        
        # Widgets para estilizar com Bootstrap (como nos seus outros formulários)
        widgets = {
            'supervisor_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'supervisor_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'supervisor_cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'supervisor_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@empresa.com'}),
            # Estes 'type': 'date' fazem o navegador mostrar um calendário
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), 
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        
# Em autenticacao/forms.py

# ... (outros imports e formulários) ...

class TermoCompromissoForm(forms.Form):
    """
    Este formulário representa os campos EDITÁVEIS
    do documento TERMO-DE-COMPROMISSO.html.
    Os dados do aluno (nome, CPF, etc.) virão do 'request.user'.
    Os dados da empresa serão preenchidos pelo aluno.
    """
    
    # Dados da Empresa (Concedente)
    concedente_nome = forms.CharField(label="Nome da Concedente (Empresa)")
    concedente_cnpj = forms.CharField(label="CNPJ da Concedente")
    concedente_rua = forms.CharField(label="Rua", max_length=150)
    concedente_numero = forms.CharField(label="Nº", max_length=10)
    concedente_bairro = forms.CharField(label="Bairro", max_length=100)
    concedente_cidade_uf = forms.CharField(label="Cidade-UF", max_length=100) 
    concedente_cep = forms.CharField(label="CEP", max_length=9) 
    concedente_representante = forms.CharField(label="Nome do Representante da Concedente")
    concedente_email = forms.EmailField(label="Email da Concedente", required=False)
    concedente_telefone = forms.CharField(label="Telefone da Concedente", required=False)

    # Dados do Supervisor
    supervisor_nome = forms.CharField(label="Nome do Supervisor (funcionário da Concedente)")

    # Dados do Estágio
    data_inicio = forms.DateField(label="Data de Início (___/___/____)", widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(label="Data de Término (___/___/____)", widget=forms.DateInput(attrs={'type': 'date'}))
    carga_horaria_diaria = forms.IntegerField(label="Horas Diárias", min_value=1, max_value=8)
    carga_horaria_semanal = forms.IntegerField(label="Horas Semanais", min_value=1, max_value=40)
    
    # Dados da Apólice de Seguro
    apolice_numero = forms.CharField(label="Nº da Apólice de Seguro")
    apolice_empresa = forms.CharField(label="Nome da Seguradora")
    
    # Campo Orientador
    orientador = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(tipo='professor').order_by('first_name', 'last_name'), # Corrigido order_by
        label="Professor(a) Orientador(a) da Escola",
        required=True, # Ajuste se necessário
        empty_label="-- Selecione o Professor --",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    # Campo Anexo PDF
    anexo_assinaturas = forms.FileField(
        label="Anexar aqui o PDF",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'})
    )
    
    
    # ==========================================================
    # MÉTODO __init__ CORRIGIDO
    # ==========================================================
    def __init__(self, *args, **kwargs):
        # Capturamos o valor inicial do orientador passado pela view
        orientador_initial = kwargs.pop('orientador_initial', None)
        
        # CHAMAMOS SUPER() PRIMEIRO
        super().__init__(*args, **kwargs)
        
        # Agora, 'self.errors' existe (está vazio em GET, preenchido em POST inválido)

        for field_name, field in self.fields.items():
            
            # Ignora os campos que NÃO devem ser 'inline'
            if field_name not in ['orientador', 'anexo_assinaturas']: 
                attrs = {'class': 'inline-input'} # Usa a classe inline
                
                # Define o tipo de input para datas e números
                if 'data' in field_name:
                    attrs['type'] = 'date'
                elif isinstance(field, forms.IntegerField):
                    attrs['type'] = 'number'
                
                # ================================================
                # CORREÇÃO: Verificamos 'self.errors' (do formulário)
                # e não 'field.errors' (que não existe aqui)
                # ================================================
                if self.errors.get(field_name):
                    attrs['class'] += ' is-invalid' # Adiciona a classe de erro
                
                # Atualiza o widget do campo
                field.widget.attrs.update(attrs)
            
            # Define o valor inicial para o dropdown 'orientador', se foi passado
            elif field_name == 'orientador' and orientador_initial:
                 self.initial['orientador'] = orientador_initial
    # ==========================================================