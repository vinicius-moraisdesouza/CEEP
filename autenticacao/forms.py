from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, get_user_model
from django.forms import modelformset_factory, BaseModelFormSet
from core.models import Turma, AlunoTurma, ProfessorMateriaAnoCursoModalidade, Curso
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