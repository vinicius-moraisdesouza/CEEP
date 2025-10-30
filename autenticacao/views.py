from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from collections import defaultdict, OrderedDict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils.timezone import now
from core.decorators import role_required
import datetime

from .forms import (
    EmailAuthenticationForm,
    ProfessorCreateForm,
    ProfessorMateriaAnoCursoModalidadeFormSet,
    ProfessorMateriaAnoCursoModalidadeForm,
    AlunoCreateForm,
    ServidorCreateForm,
    EstagioCreateForm,
    TermoCompromissoForm
)

from core.models import Materia, Turma, CustomUser, ProfessorMateriaAnoCursoModalidade, AlunoTurma, Nota, Estagio, DocumentoEstagio


# === AUTENTICAÇÃO ===

@login_required
def redirect_por_tipo(request):
    if request.user.tipo == 'admin':
        return redirect('admin_dashboard')
    elif request.user.tipo == 'professor':
        return redirect('professor_dashboard')
    elif request.user.tipo == 'aluno':
        return redirect('aluno_dashboard')
    elif request.user.tipo == 'servidor' or request.user.tipo == 'diretor':
        return redirect('servidor_dashboard')
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect_por_tipo(request)
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                messages.success(
                    request, f"Bem-vindo(a), {user.first_name or user.email}")
                if user.tipo == 'admin':
                    return redirect('admin_dashboard')
                elif user.tipo == 'professor':
                    return redirect('professor_dashboard')
                elif user.tipo == 'aluno':
                    return redirect('aluno_dashboard')
                messages.warning(request, "Tipo de usuário não reconhecido.")
                return redirect('login')
            else:
                messages.error(request, "Email ou senha inválidos.")
        else:
            messages.error(request, "Email ou senha inválidos.")
    else:
        form = EmailAuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Você foi desconectado(a).")
    return redirect('login')


@login_required
def ver_perfil(request):
    user = request.user
    turmas = []
    vinculos = []

    if user.tipo == 'aluno':
        turmas = Turma.objects.filter(alunoturma__aluno=user)

    elif user.tipo == 'professor':
        vinculos = ProfessorMateriaAnoCursoModalidade.objects.filter(professor=user).select_related('materia', 'curso')

    return render(request, 'perfil/ver_perfil.html', {
        'user': user,
        'turmas': turmas,
        'vinculos': vinculos
    })

@login_required
@role_required('professor', 'aluno')
def alterar_senha(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            print(f"[LOG] Senha alterada por: {user.username} em {now()}")
            user.senha_temporaria = False
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Senha atualizada com sucesso.")
            return redirect('ver_perfil')
        else:
            messages.error(request, "Corrija os erros abaixo.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'perfil/alterar_senha.html', {'form': form})

# === DASHBOARDS ===

@login_required
@role_required('admin')
def admin_dashboard_view(request):
    return render(request, 'admin/admin_dashboard.html')

@login_required
@role_required('professor')
def professor_dashboard_view(request):
    vinculos = ProfessorMateriaAnoCursoModalidade.objects.filter(
        professor=request.user
    ).select_related('materia', 'curso')

    context = {
        'vinculos': vinculos
    }
    return render(request, 'professor/professor_dashboard.html', context)

@login_required
@role_required('aluno')
def aluno_dashboard_view(request):
    aluno = request.user
    notas = Nota.objects.filter(aluno=aluno).select_related('materia', 'turma')

    return render(request, 'aluno/aluno_dashboard.html', {
        'notas': notas,
        'aluno': aluno
    })
    
@login_required
@role_required('servidor', 'diretor') # Permite acesso a ambos os tipos
def servidor_dashboard_view(request):
    """
    Dashboard para Servidores e Diretores, focado na gestão de estágios.
    """
    
    # --- Métricas Principais ---
    
    # Conta o total de processos de estágio abertos (status "Em Andamento")
    # (Estes status vêm do models.py)
    estagios_ativos_count = Estagio.objects.filter(status_geral="Em Andamento").count()
    
    # Conta documentos que exigem ação (status "EM_VERIFICACAO")
    documentos_pendentes_count = DocumentoEstagio.objects.filter(
        status='EM_VERIFICACAO'
    ).count()
    
    # Conta o total de documentos já finalizados/arquivados
    documentos_finalizados_count = DocumentoEstagio.objects.filter(
        status='FINALIZADO'
    ).count()

    # --- Lista de Ações Pendentes ---
    
    # Busca os 10 documentos mais recentes que precisam de verificação
    documentos_pendentes = DocumentoEstagio.objects.filter(
        status='EM_VERIFICACAO'
    ).select_related('estagio__aluno').order_by('-data_upload')[:10]

    
    context = {
        'estagios_ativos_count': estagios_ativos_count,
        'documentos_pendentes_count': documentos_pendentes_count,
        'documentos_finalizados_count': documentos_finalizados_count,
        'documentos_pendentes': documentos_pendentes,
        'user': request.user
    }
    
    # O template que vamos criar a seguir
    return render(request, 'servidor/servidor_dashboard.html', context)


# === ADMIN - PROFESSORES ===

@login_required
@role_required('admin')
def gerenciar_professores(request):
    # ORDENAÇÃO: Ordena pelo nome e sobrenome
    professores = CustomUser.objects.filter(tipo='professor').order_by('first_name', 'last_name') 
    return render(request, 'admin/professor_crud/gerenciar_professores.html', {'professores': professores})


@login_required
@role_required('admin')
def ver_detalhes_professor(request, professor_id):
    professor = get_object_or_404(CustomUser, id=professor_id, tipo='professor')
    vinculos = ProfessorMateriaAnoCursoModalidade.objects.filter(professor=professor).select_related('materia', 'curso')

    return render(request, 'admin/professor_crud/detalhes_professor.html', {
        'professor': professor,
        'vinculos': vinculos,
    })


@login_required
@role_required('admin')
def cadastrar_professor(request):
    if request.method == 'POST':
        form = ProfessorCreateForm(request.POST)
        formset = ProfessorMateriaAnoCursoModalidadeFormSet(request.POST, queryset=ProfessorMateriaAnoCursoModalidade.objects.none())

        if form.is_valid() and formset.is_valid():
            professor = form.save() 

            instances = formset.save(commit=False)
            for instance in instances:
                instance.professor = professor
                instance.save()
            
            messages.success(request, "Professor cadastrado com sucesso.")
            return redirect('gerenciar_professores')
        else:
            messages.error(request, "Erro ao cadastrar. Verifique os campos do professor e dos vínculos.")
    else:
        form = ProfessorCreateForm()
        formset = ProfessorMateriaAnoCursoModalidadeFormSet(queryset=ProfessorMateriaAnoCursoModalidade.objects.none())

    return render(request, 'admin/professor_crud/cadastrar_professor.html', {
        'form': form,
        'formset': formset
    })


@login_required
@role_required('admin')
def editar_professor(request, professor_id):
    professor = get_object_or_404(CustomUser, id=professor_id, tipo='professor')
    
    form = ProfessorCreateForm(request.POST or None, instance=professor)
    formset = ProfessorMateriaAnoCursoModalidadeFormSet(
        request.POST or None,
        queryset=ProfessorMateriaAnoCursoModalidade.objects.filter(professor=professor)
    )

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        form.save()
        
        instances = formset.save(commit=False)
        for instance in instances:
            instance.professor = professor
            instance.save()
        
        for obj in formset.deleted_objects:
            obj.delete()

        messages.success(request, "Professor atualizado com sucesso.")
        return redirect('gerenciar_professores')

    return render(request, 'admin/professor_crud/editar_professor.html', {
        'form': form,
        'formset': formset,
        'professor': professor
    })


@login_required
@role_required('admin')
def remover_professor(request, professor_id):
    professor = get_object_or_404(CustomUser, id=professor_id, tipo='professor')

    if request.method == 'POST':
        professor.delete()
        messages.success(request, "Professor removido com sucesso.")
        return redirect('gerenciar_professores')

    return render(request, 'admin/professor_crud/remover_professor.html', {'professor': professor})


# === ADMIN - ALUNOS ===

@login_required
@role_required('admin')
def gerenciar_alunos(request):
    # ORDENAÇÃO: Ordena pelo nome e sobrenome
    alunos = CustomUser.objects.filter(tipo='aluno').prefetch_related('alunoturma_set__turma').order_by('first_name', 'last_name')
    return render(request, 'admin/aluno_crud/gerenciar_alunos.html', {'alunos': alunos})


@login_required
@role_required('admin')
def cadastrar_aluno(request):
    if request.method == 'POST':
        # ==========================================================
        # <<< BLOCO DE PRINT PARA DEBUG (ADICIONADO DE VOLTA) >>>
        # ==========================================================
        print("="*30)
        print("🧾 DADOS RECEBIDOS DO FORMULÁRIO (NO BACKEND):")
        print(f"Curso ID: {request.POST.get('curso')}")
        print(f"Ano/Módulo: {request.POST.get('ano_modulo')}")
        print(f"Turno: {request.POST.get('turno')}")
        print(f"Turma ID: {request.POST.get('turma')}")
        print("="*30)
        # ==========================================================

        form = AlunoCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno cadastrado com sucesso.")
            return redirect('gerenciar_alunos')
        else:
            # Também é útil imprimir os erros do formulário para debug
            print("\n⚠️ ERROS DE VALIDAÇÃO DO FORMULÁRIO:")
            print(form.errors.as_json())
            print("-" * 30 + "\n")
            messages.error(request, "Erro ao salvar. Verifique os campos.")
    else:
        form = AlunoCreateForm()
        
    return render(request, 'admin/aluno_crud/cadastrar_aluno.html', {'form': form})


@login_required
@role_required('admin')
def editar_aluno(request, aluno_id):
    aluno = get_object_or_404(CustomUser, id=aluno_id, tipo='aluno')

    if request.method == 'POST':
        curso_id = request.POST.get('curso')
        ano_modulo = request.POST.get('ano_modulo')
        turno = request.POST.get('turno')

        # --- Debug opcional ---
        print("="*40)
        print("🧾 DADOS RECEBIDOS NO POST (Editar Aluno):")
        print(f"Curso ID: {curso_id}")
        print(f"Ano/Módulo: {ano_modulo}")
        print(f"Turno: {turno}")
        print(f"Turma ID: {request.POST.get('turma')}")
        print("="*40)

        form = AlunoCreateForm(request.POST, instance=aluno)

        # --- 🔧 Repopula dinamicamente as opções antes de validar ---
        turmas_queryset = Turma.objects.all()
        if curso_id:
            turmas_queryset = turmas_queryset.filter(curso_id=curso_id)
        if ano_modulo:
            turmas_queryset = turmas_queryset.filter(ano_modulo=ano_modulo)
        if turno:
            turmas_queryset = turmas_queryset.filter(turno=turno)

        # Atualiza os campos dependentes
        form.fields['turma'].queryset = turmas_queryset
        form.fields['turno'].choices = [
            (valor, label) for valor, label in Turma.TURNO_CHOICES
            if valor in turmas_queryset.values_list('turno', flat=True)
        ]

        # --- Validação ---
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno atualizado com sucesso.")
            return redirect('gerenciar_alunos')
        else:
            print("\n⚠️ ERROS DE VALIDAÇÃO:")
            print(form.errors.as_json())
            print("-" * 40)
            messages.error(request, "Erro ao salvar. Verifique os campos.")
    else:
        form = AlunoCreateForm(instance=aluno)

        # --- 🔄 Pré-carrega selects com base na turma atual ---
        if hasattr(aluno, 'alunoturma_set') and aluno.alunoturma_set.exists():
            turma_atual = aluno.alunoturma_set.first().turma
            turmas_queryset = Turma.objects.filter(
                curso=turma_atual.curso,
                ano_modulo=turma_atual.ano_modulo,
                turno=turma_atual.turno
            )
            form.fields['turma'].queryset = turmas_queryset
            form.fields['turno'].choices = [
                (turma_atual.turno, turma_atual.get_turno_display())
            ]

    context = {
        'form': form,
        'aluno': aluno
    }
    return render(request, 'admin/aluno_crud/editar_aluno.html', context)


@login_required
@role_required('admin')
def remover_aluno(request, aluno_id):
    aluno = get_object_or_404(CustomUser, id=aluno_id, tipo='aluno')

    if request.method == 'POST':
        aluno.delete()
        messages.success(request, "Aluno removido com sucesso.")
        return redirect('gerenciar_alunos')

    return render(request, 'admin/aluno_crud/remover_aluno.html', {'aluno': aluno})


@login_required
@role_required('admin')
def ver_detalhes_aluno(request, aluno_id):
    aluno = get_object_or_404(CustomUser, id=aluno_id, tipo='aluno')
    turmas = aluno.alunoturma_set.all()
    return render(request, 'admin/aluno_crud/detalhes_aluno.html', {'aluno': aluno, 'turmas': turmas})

# === ADMIN - SERVIDORES ===

@login_required
@role_required('admin')
def gerenciar_servidores(request):
    # Adicionamos .order_by('first_name', 'last_name') para ordenar pelo nome e sobrenome
    servidores = CustomUser.objects.filter(tipo='servidor').order_by('first_name', 'last_name')
    return render(request, 'admin/servidor_crud/gerenciar_servidores.html', {'servidores': servidores})

@login_required
@role_required('admin')
def cadastrar_servidor(request):
    if request.method == 'POST':
        form = ServidorCreateForm(request.POST)
        if form.is_valid():
            servidor = form.save(commit=False)
    
    # ✅ CORREÇÃO: Pega o tipo escolhido do formulário
            tipo_escolhido = form.cleaned_data['tipo_usuario']
            servidor.tipo = tipo_escolhido 
            servidor.username = servidor.cpf
            servidor.email = f"{servidor.cpf}@servidor.com"
            servidor.set_password("Senha123#")
            servidor.senha_temporaria = True
            servidor.save()
            messages.success(request, "Servidor cadastrado com sucesso.")
            return redirect('gerenciar_servidores')
        else:
            messages.error(request, "Erro ao cadastrar o servidor. Verifique os campos.")
    else:
        form = ServidorCreateForm()
    return render(request, 'admin/servidor_crud/cadastrar_servidor.html', {'form': form})


# Em autenticacao/views.py

@login_required
@role_required('admin')
def editar_servidor(request, servidor_id):
    servidor = get_object_or_404(CustomUser, id=servidor_id, tipo__in=['servidor', 'diretor'])

    if request.method == 'POST':
        form = ServidorCreateForm(request.POST, instance=servidor)
        if form.is_valid():
            tipo_usuario = form.cleaned_data['tipo_usuario']
            eixo = form.cleaned_data.get('eixo')

            user = form.save(commit=False)
            
            user.tipo = tipo_usuario
            if tipo_usuario == 'servidor':
                user.eixo = eixo
            else:  
                user.eixo = None
            
            user.save()

            messages.success(request, "Dados atualizados com sucesso.")
            return redirect('gerenciar_servidores')
    else:
        initial_data = {'tipo_usuario': servidor.tipo}
        
        form = ServidorCreateForm(instance=servidor, initial=initial_data)

    context = {
        'form': form,
        'servidor': servidor,
    }
    return render(request, 'admin/servidor_crud/editar_servidor.html', context)

@login_required
@role_required('admin')
def remover_servidor(request, servidor_id):
    servidor = get_object_or_404(CustomUser, id=servidor_id, tipo='servidor')
    if request.method == 'POST':
        servidor.delete()
        messages.success(request, "Servidor removido com sucesso.")
        return redirect('gerenciar_servidores')
    return render(request, 'admin/servidor_crud/remover_servidor.html', {'servidor': servidor})


@login_required
@role_required('admin')
def ver_detalhes_servidor(request, servidor_id):
    servidor = get_object_or_404(CustomUser, id=servidor_id, tipo='servidor')
    
    context = {
        'servidor': servidor
    }
    return render(request, 'admin/servidor_crud/detalhes_servidor.html', context)

# === VIEWS DE API ===

def get_opcoes_turma(request):
    curso_id = request.GET.get('curso_id')
    ano_modulo = request.GET.get('ano_modulo')
    turno = request.GET.get('turno')
    target = request.GET.get('target')

    queryset = Turma.objects.all()

    if curso_id: queryset = queryset.filter(curso_id=curso_id)
    if ano_modulo: queryset = queryset.filter(ano_modulo=ano_modulo)
    if turno: queryset = queryset.filter(turno=turno)

    if target == 'ano_modulo':
        data = list(queryset.order_by('ano_modulo').values_list('ano_modulo', flat=True).distinct())
        return JsonResponse({'options': data})

    if target == 'turno':
        turnos_existentes = list(queryset.values_list('turno', flat=True).distinct())
        data = []
        for valor, display in Turma.TURNO_CHOICES:
            if valor in turnos_existentes:
                data.append({'value': valor, 'display': display})
        return JsonResponse({'options': data})

    if target == 'turma':
        data = []
        for turma_obj in queryset.order_by('turma'):
            data.append({'id': turma_obj.id, 'display': turma_obj.nome_curto})
        return JsonResponse({'options': data})

    return JsonResponse({}, status=400)

def debug_log(request):
    print("\n===== DEBUG RECEBIDO DO FRONT =====")
    print("Curso:", request.GET.get('curso'))
    print("Ano/Módulo:", request.GET.get('ano_modulo'))
    print("Turno:", request.GET.get('turno'))
    print("Turma:", request.GET.get('turma'))
    print("===================================\n")
    return JsonResponse({'status': 'ok'})

# === ADMIN - TURMAS ===

@login_required
@role_required('admin')
def listar_turmas(request):
    turmas = Turma.objects.all()
    return render(request, 'admin/turmas_crud/listar_turmas.html', {'turmas': turmas})


@login_required
@role_required('admin')
def detalhar_turma(request, turma_id):
    turma = get_object_or_404(Turma, id=turma_id)
    alunos = CustomUser.objects.filter(alunoturma__turma=turma, tipo='aluno')
    return render(request, 'admin/turmas_crud/detalhar_turma.html', {'turma': turma, 'alunos': alunos})

# === ADMIN - MATÉRIAS ===

@login_required
@role_required('admin')
def listar_materias(request):
    materias = Materia.objects.all()
    return render(request, 'admin/materias_crud/listar_materias.html', {'materias': materias})


@login_required
@role_required('admin')
def detalhar_materia(request, materia_id):
    materia = get_object_or_404(Materia, id=materia_id)
    vinculos = ProfessorMateriaAnoCursoModalidade.objects.filter(materia=materia).select_related('professor', 'turma')

    professores_com_turmas = defaultdict(list)
    for v in vinculos:
        professores_com_turmas[v.professor].append(v.turma.nome)

    context_data = [(prof, turmas) for prof, turmas in professores_com_turmas.items()]
    return render(request, 'admin/materias_crud/detalhar_materia.html', {
        'materia': materia,
        'professores_com_turmas': context_data
    })

# === PROFESSOR - MATÉRIAS-ANO-CURSO-MODALIDADE ===

@login_required
@role_required('professor')
def listar_turmas_vinculadas(request, vinculo_id):
    vinculo = get_object_or_404(ProfessorMateriaAnoCursoModalidade, id=vinculo_id, professor=request.user)

    turmas = Turma.objects.filter(
        curso=vinculo.curso,
        ano_modulo=vinculo.ano_modulo,
        modalidade=vinculo.modalidade
    )

    context = {
        'vinculo': vinculo,
        'turmas': turmas
    }
    return render(request, 'professor/listar_turmas_vinculadas.html', context)

@login_required
@role_required('professor')
def detalhar_turma_professor(request, materia_id, turma_id):
    materia = get_object_or_404(Materia, id=materia_id)
    turma = get_object_or_404(Turma, id=turma_id)

    vinculado = ProfessorMateriaAnoCursoModalidade.objects.filter(
        professor=request.user,
        materia=materia,
        curso=turma.curso,
        ano_modulo=turma.ano_modulo,
        modalidade=turma.modalidade
    ).exists()

    if not vinculado:
        messages.error(request, "Você não tem permissão para lecionar esta matéria nesta turma.")
        return redirect('professor_dashboard')

    alunos = CustomUser.objects.filter(tipo='aluno', alunoturma__turma=turma).distinct()
    notas_dict = {nota.aluno.id: nota for nota in Nota.objects.filter(materia=materia, turma=turma)}
    
    context = {
        'materia': materia, 'turma': turma, 'alunos': alunos, 'notas_dict': notas_dict
    }
    return render(request, 'professor/detalhar_turma.html', context)
    
@login_required
@role_required('professor')
def ver_turma_professor(request, materia_id, turma_id):
    materia = get_object_or_404(Materia, id=materia_id)
    turma = get_object_or_404(Turma, id=turma_id)

    if not ProfessorMateriaAnoCursoModalidade.objects.filter(professor=request.user, materia=materia, turma=turma).exists():
        messages.error(request, "Você não tem acesso a essa turma.")
        return redirect('professor_dashboard')

    alunos = CustomUser.objects.filter(tipo='aluno', alunoturma__turma=turma).distinct()
    notas_dict = {nota.aluno_id: nota for nota in Nota.objects.filter(materia=materia, turma=turma)}

    return render(request, 'professor/detalhar_turma.html', {
        'materia': materia,
        'turma': turma,
        'alunos': alunos,
        'notas_dict': notas_dict
    })

@login_required
@role_required('professor')
def ver_detalhes_aluno_professor(request, aluno_id):
    aluno = get_object_or_404(CustomUser, id=aluno_id, tipo='aluno')
    turmas = Turma.objects.filter(alunoturma__aluno=aluno)
    return render(request, 'professor/detalhes_aluno.html', {'aluno': aluno, 'turmas': turmas})
    

@login_required
@role_required('professor')
@csrf_exempt
def inserir_nota(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Requisição inválida"}, status=400)

    aluno_id = request.POST.get("aluno_id")
    materia_id = request.POST.get("materia_id")
    turma_id = request.POST.get("turma_id")

    aluno = get_object_or_404(CustomUser, id=aluno_id)
    materia = get_object_or_404(Materia, id=materia_id)
    turma = get_object_or_404(Turma, id=turma_id)

    nota_obj, _ = Nota.objects.get_or_create(aluno=aluno, materia=materia, turma=turma)

    def parse_optional_float(val):
        try:
            if val == '' or val is None:
                return None
            f = float(val.replace(',', '.')) 
            return min(f, 100) 
        except (ValueError, TypeError):
            return None

    nota_obj.nota_1 = parse_optional_float(request.POST.get("nota_1"))
    nota_obj.nota_2 = parse_optional_float(request.POST.get("nota_2"))
    nota_obj.nota_3 = parse_optional_float(request.POST.get("nota_3"))
    nota_obj.nota_recuperacao = parse_optional_float(request.POST.get("nota_recuperacao"))

    try:
        nota_obj.save() 
    except Exception as e:
        return JsonResponse({"error": f"Erro ao salvar a nota: {str(e)}"}, status=500)

    status = nota_obj.status_final or "Pendente"
    badge_map = {
        "Aprovado": "bg-success text-white",
        "Reprovado na Final": "bg-danger text-white",
        "Reprovado": "bg-danger-subtle text-dark",
        "Pendente": "bg-secondary text-white", 
    }
    badge_class = badge_map.get(status, "bg-secondary text-white")

    return JsonResponse({
        "status": status, 
        "badge_class": badge_class,
        "media_final": f"{nota_obj.media_final:.1f}" if nota_obj.media_final is not None else "---"
    })


# ==========================================================
# === ALUNO - BOLETIM - ESTÁGIO 
# ==========================================================

@login_required
@role_required('aluno')
def ver_boletim_aluno(request):
    """
    (Esta view permanece a mesma)
    Mostra o boletim do aluno.
    """
    aluno = request.user
    # Correção: Usar alunoturma_set para encontrar as turmas
    turmas_ids = AlunoTurma.objects.filter(aluno=aluno).values_list('turma_id', flat=True)
    # Correção: Filtrar matérias pelas turmas do aluno
    materias = Materia.objects.filter(turmas__id__in=turmas_ids).distinct()

    boletim = []
    for materia in materias:
        nota = Nota.objects.filter(aluno=aluno, materia=materia).first()
        boletim.append({'materia': materia, 'nota': nota})

    # Certifique-se que o caminho do template está correto
    return render(request, 'aluno/boletim/boletim.html', {'boletim': boletim, 'aluno': aluno})


@login_required
@role_required('aluno')
def gestao_estagio_aluno(request):
    """
    View "Gestora" (Dispatcher) - VERSÃO CORRIGIDA.
    Esta é a view chamada pelo botão no dashboard.

    1. Verifica se o aluno já tem um 'Estagio' (Dossiê).
    2. Se não tiver, CRIA um 'Estagio' (com datas padrão) e todos 
       os 'DocumentoEstagio' obrigatórios em status 'RASCUNHO'.
    3. Redireciona o aluno para a "Central de Documentos" (detalhes_estagio_aluno).
    """
    # Procura pelo Dossiê de Estágio do aluno.
    # O 'get_or_create' cria o objeto Estagio se ele não existir.
    
    # --- MODIFICAÇÃO AQUI ---
    hoje = datetime.date.today() # Pega a data de hoje
    estagio, criado = Estagio.objects.get_or_create(
        aluno=request.user,
        # O 'defaults' só é usado se o objeto for criado agora
        defaults={
            'status_geral': 'Rascunho (Aguardando preenchimento)',
            'data_inicio': hoje, # <-- Valor padrão adicionado
            'data_fim': hoje     # <-- Valor padrão adicionado
            # Verifique se mais algum campo obrigatório do Estagio 
            # precisa de um valor default aqui
        }
    )
    # --- FIM DA MODIFICAÇÃO ---

    if criado:
        # Se o Dossiê foi criado agora, vamos também criar os
        # documentos obrigatórios que definimos no models.py

        # Pega todos os tipos de documento definidos em models.py
        tipos_de_documento = DocumentoEstagio.TIPO_DOCUMENTO_CHOICES

        documentos_para_criar = []
        for tipo_id, nome_legivel in tipos_de_documento:
            documentos_para_criar.append(
                DocumentoEstagio(
                    estagio=estagio,
                    tipo_documento=tipo_id,
                    status='RASCUNHO' # Começa como Rascunho
                )
            )

        # Cria todos os documentos no banco de dados de uma só vez
        DocumentoEstagio.objects.bulk_create(documentos_para_criar)
        messages.info(request, "Seu Dossiê de Estágio foi criado. Por favor, preencha os documentos necessários.")

    # Envia o aluno para a "Central de Documentos"
    return redirect('detalhes_estagio_aluno')


@login_required
@role_required('aluno')
def detalhes_estagio_aluno(request):
    """
    A "Central de Documentos" do Aluno - VERSÃO ATUALIZADA COM ORDENAÇÃO.
    Mostra os detalhes do estágio e a lista de documentos na ordem definida.
    """
    estagio = get_object_or_404(Estagio, aluno=request.user)

    # 1. Busca todos os documentos ligados a esse estágio
    documentos_qs = DocumentoEstagio.objects.filter(estagio=estagio)

    # 2. Define a ordem desejada (use os IDs exatos do TIPO_DOCUMENTO_CHOICES em models.py)
    ordem_desejada = [
        'TERMO_COMPROMISSO',
        'AVALIACAO_ORIENTADOR', # Certifique-se que este ID existe em TIPO_DOCUMENTO_CHOICES
        'AVALIACAO_SUPERVISOR', # Certifique-se que este ID existe em TIPO_DOCUMENTO_CHOICES
        'FICHA_PESSOAL',        # Certifique-se que este ID existe em TIPO_DOCUMENTO_CHOICES
        'FICHA_IDENTIFICACAO',  # Certifique-se que este ID existe em TIPO_DOCUMENTO_CHOICES
        # Adicione os OUTROS IDs de TIPO_DOCUMENTO_CHOICES aqui, na ordem que preferir
        'COMP_RESIDENCIA',
        'COMP_AGUA_LUZ',
        'ID_CARD',
        'SUS_CARD',
        'VACINA_CARD',
        'APOLICE_SEGURO',
    ]

    # 3. Cria um dicionário ordenado para garantir a ordem
    documentos_dict = OrderedDict()
    # Adiciona documentos na ordem desejada
    for tipo in ordem_desejada:
        documentos_dict[tipo] = None # Inicializa com None
    # Preenche o dicionário com os documentos encontrados
    for doc in documentos_qs:
        if doc.tipo_documento in documentos_dict:
            documentos_dict[doc.tipo_documento] = doc

    # Adiciona quaisquer documentos encontrados que não estavam na ordem_desejada (caso TIPO_DOCUMENTO_CHOICES mude)
    for doc in documentos_qs:
        if doc.tipo_documento not in documentos_dict:
             documentos_dict[doc.tipo_documento] = doc


    # 4. Cria a lista final ordenada (removendo None se algum tipo não foi encontrado)
    documentos_ordenados = [doc for doc in documentos_dict.values() if doc is not None]


    context = {
        'estagio': estagio,
        'documentos': documentos_ordenados # Envia a lista ORDENADA para o template
    }

    return render(request, 'aluno/estagio/detalhes_estagio.html', context)


@login_required
@role_required('aluno')
def visualizar_documento_estagio(request, documento_id):
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    estagio = documento.estagio

    # Define qual template será usado
    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_VISUALIZAR.html'
    else:
        messages.error(request, "A visualização para este tipo de documento ainda não foi criada.")
        return redirect('detalhes_estagio_aluno')

    dados = documento.dados_formulario or {}

    # 🔧 Converte campos de data (string → datetime.date)
    for campo in ['data_inicio', 'data_fim']:
        valor = dados.get(campo)
        if isinstance(valor, str):
            try:
                dados[campo] = datetime.date.fromisoformat(valor)
            except ValueError:
                pass

    # ✅ Verifica se o arquivo PDF anexado realmente existe
    pdf_existe = False
    if documento.pdf_supervisor_assinado:
        try:
            pdf_existe = documento.pdf_supervisor_assinado.storage.exists(documento.pdf_supervisor_assinado.name)
        except Exception:
            pdf_existe = False

    context = {
        'documento': documento,
        'aluno': request.user,
        'estagio': estagio,
        'dados': dados,
        'pdf_existe': pdf_existe,  # adiciona flag segura para o template
    }

    return render(request, template_name, context)


@login_required
@role_required('aluno')
def upload_pdf_assinado(request, documento_id):
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)

    if request.method == 'POST' and 'pdf_supervisor_assinado' in request.FILES:
        documento.pdf_supervisor_assinado = request.FILES['pdf_supervisor_assinado']
        documento.save()
        messages.success(request, 'PDF anexado com sucesso!')
    else:
        messages.error(request, 'Nenhum arquivo foi selecionado.')

    return redirect('visualizar_documento_estagio', documento_id=documento.id)

@login_required
@role_required('aluno')
def remover_pdf_assinado(request, documento_id):
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)

    if request.method == 'POST':
        if documento.pdf_supervisor_assinado:
            # Apaga o arquivo físico e limpa o campo do modelo
            documento.pdf_supervisor_assinado.delete(save=False)
            documento.pdf_supervisor_assinado = None
            documento.save()
            messages.success(request, "O PDF anexado foi removido com sucesso.")
        else:
            messages.warning(request, "Nenhum PDF estava anexado a este documento.")

    return redirect('visualizar_documento_estagio', documento_id=documento.id)

@login_required
@role_required('aluno')
def assinar_documento_aluno(request, documento_id):
    """
    Registra a assinatura do aluno no documento.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    
    # Verifica se o documento está no status correto para assinar
    # (Deve ter sido salvo pelo menos uma vez, mudando de RASCUNHO para AGUARDANDO_ASSINATURAS)
    if documento.status == 'RASCUNHO':
         messages.warning(request, "Este documento não está pronto para ser assinado. Edite e Salve o documento primeiro.")
         return redirect('visualizar_documento_estagio', documento_id=documento.id)

    # Verifica se já não foi assinado
    if documento.assinado_aluno_em:
        messages.warning(request, "Você já assinou este documento.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)
        
    # --- Executa a Ação de Assinar ---
    documento.assinado_aluno_em = now() # 'now' deve estar importado de django.utils.timezone
    documento.save()
    
    messages.success(request, "Documento assinado com sucesso!")
    return redirect('visualizar_documento_estagio', documento_id=documento.id)


@login_required
@role_required('aluno')
def compartilhar_documento_aluno(request, documento_id):
    """
    "Conclui" e "Compartilha" o documento com a escola.
    Muda o status para 'EM_VERIFICACAO' e torna 'publico'.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    estagio = documento.estagio

    # Requisitos para compartilhar:
    # 1. Deve estar assinado pelo aluno
    if not documento.assinado_aluno_em:
        messages.error(request, "Você precisa assinar o documento antes de compartilhá-lo.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)
    
    # 2. O professor orientador deve ter sido selecionado
    if not estagio.orientador:
        messages.error(request, "Você precisa selecionar um Professor Orientador (na página 'Editar') antes de compartilhar.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)
        
    # 3. Não pode já ter sido compartilhado
    if documento.status == 'EM_VERIFICACAO' or documento.status == 'FINALIZADO':
        messages.warning(request, "Este documento já foi compartilhado.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)

    # --- Executa a Ação de Compartilhar ---
    documento.status = 'EM_VERIFICACAO' # Envia para o Servidor/Professor
    documento.publico = True # Torna visível
    documento.save()
    
    # Opcional: Aqui você pode adicionar a lógica para enviar um email ao 'estagio.orientador'
    
    messages.success(request, f"Documento concluído e compartilhado com {estagio.orientador.get_full_name()}!")
    return redirect('visualizar_documento_estagio', documento_id=documento.id)


@login_required
@role_required('aluno')
def preencher_documento_estagio(request, documento_id):
    """
    VIEW ATUALIZADA: Agora é a página de "Editar".
    Carrega o formulário para editar o documento.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    estagio = documento.estagio # Pegamos o objeto Estagio para salvar o orientador

    # Verifica qual formulário e template usar baseado no tipo de documento
    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        FormClass = TermoCompromissoForm
        # --- MODIFICAÇÃO AQUI ---
        # O template agora é o de EDIÇÃO
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_EDITAR.html' 
    # (Futuramente, adicionar 'elif' para outros tipos de documento)
    else:
        messages.error(request, f"O preenchimento online para '{documento.get_tipo_documento_display()}' ainda não está disponível.")
        return redirect('detalhes_estagio_aluno')

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, orientador_initial=estagio.orientador)
        
        if form.is_valid():
            dados_para_json = form.cleaned_data.copy()
            
            # 1. Lidar com o Orientador
            orientador_selecionado = dados_para_json.pop('orientador', None) 
            if orientador_selecionado:
                estagio.orientador = orientador_selecionado
                estagio.save() 

            # 2. Lidar com o Anexo PDF
            anexo_pdf = dados_para_json.pop('anexo_assinaturas', None) 
            if anexo_pdf:
                documento.pdf_supervisor_assinado = anexo_pdf
            elif anexo_pdf is False: 
                documento.pdf_supervisor_assinado = None
            
            # 3. Converter datas para strings (Correção do bug anterior)
            if isinstance(dados_para_json.get('data_inicio'), datetime.date):
                dados_para_json['data_inicio'] = dados_para_json['data_inicio'].isoformat()
            if isinstance(dados_para_json.get('data_fim'), datetime.date):
                dados_para_json['data_fim'] = dados_para_json['data_fim'].isoformat()
            
            # 4. Salvar o resto dos dados no JSON
            documento.dados_formulario = dados_para_json
            
            # Atualiza o status
            if documento.status == 'RASCUNHO':
                 documento.status = 'AGUARDANDO_ASSINATURAS'
            
            documento.save() 

            messages.success(request, f"'{documento.get_tipo_documento_display()}' salvo com sucesso!")
            # Redireciona para a NOVA página de VISUALIZAÇÃO
            return redirect('visualizar_documento_estagio', documento_id=documento.id)
        else:
            messages.error(request, "Erro ao salvar. Verifique os campos preenchidos.")

    else: # (Método GET)
        initial_data = documento.dados_formulario
        form = FormClass(initial=initial_data, orientador_initial=estagio.orientador)

    context = {
        'form': form,
        'documento': documento,
        'aluno': request.user, 
        'estagio': estagio 
    }
    return render(request, template_name, context)
