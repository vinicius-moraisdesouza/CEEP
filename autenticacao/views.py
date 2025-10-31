from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from collections import defaultdict, OrderedDict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count # 🎯 ADICIONADO Q e Count
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
    ProfessorOrientadorChoiceField,
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
    elif request.user.tipo == 'servidor' or request.user.tipo == 'direcao':
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
                # 🎯 CORREÇÃO: Redirecionamento de login para servidor/direcao
                elif user.tipo == 'servidor' or user.tipo == 'direcao':
                    return redirect('servidor_dashboard')
                    
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
    # 🎯 CORREÇÃO: A lógica do dashboard foi alterada
    # para buscar DOCUMENTOS pendentes, não DOSSIÊS.
    
    vinculos = ProfessorMateriaAnoCursoModalidade.objects.filter(
        professor=request.user
    ).select_related('materia', 'curso')

    # Busca por DOCUMENTOS INDIVIDUAIS que aguardam assinatura
    documentos_pendentes = DocumentoEstagio.objects.filter(
        estagio__orientador=request.user,
        status='AGUARDANDO_ASSINATURA_PROF' 
    ).select_related('estagio__aluno')

    context = {
        'vinculos': vinculos,
        'documentos_pendentes': documentos_pendentes 
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
@role_required('servidor', 'direcao')
def servidor_dashboard_view(request):
    """
    🎯 CORREÇÃO: Esta view foi refatorada.
    - 'direcao' vê sua fila de documentos para assinar.
    - 'servidor' vê um portal de monitoramento.
    """
    context = {'user': request.user}
    
    if request.user.tipo == 'direcao':
        # Direção vê DOCUMENTOS na sua fila de assinatura
        documentos_pendentes = DocumentoEstagio.objects.filter(
            status='AGUARDANDO_ASSINATURA_DIR' 
        ).select_related('estagio__aluno', 'estagio__orientador')
        
        context['documentos_pendentes'] = documentos_pendentes
        # (Usando o nome do template que você especificou)
        template_name = 'servidor/direcao/servidor-direcao_dashboard.html'
    
    elif request.user.tipo == 'servidor':
        # Servidor Admin vê um portal de monitoramento
        # Contamos alunos no eixo do servidor
        alunos_no_eixo_count = 0
        if request.user.eixo:
            alunos_no_eixo_count = CustomUser.objects.filter(
                tipo='aluno',
                alunoturma_set__turma__curso__eixo=request.user.eixo
            ).distinct().count()
        
        context['alunos_no_eixo_count'] = alunos_no_eixo_count
        # (Usando o nome do template que você especificou)
        template_name = 'servidor/administrativo/servidor-administrativo_dashboard.html'
        
    return render(request, template_name, context)


# === ADMIN - PROFESSORES ===
# (Esta secção não foi alterada)

@login_required
@role_required('admin')
def gerenciar_professores(request):
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
# (Esta secção não foi alterada)

@login_required
@role_required('admin')
def gerenciar_alunos(request):
    alunos = CustomUser.objects.filter(tipo='aluno').prefetch_related('alunoturma_set__turma').order_by('first_name', 'last_name')
    return render(request, 'admin/aluno_crud/gerenciar_alunos.html', {'alunos': alunos})


@login_required
@role_required('admin')
def cadastrar_aluno(request):
    if request.method == 'POST':
        print("="*30)
        print("🧾 DADOS RECEBIDOS DO FORMULÁRIO (NO BACKEND):")
        print(f"Curso ID: {request.POST.get('curso')}")
        print(f"Ano/Módulo: {request.POST.get('ano_modulo')}")
        print(f"Turno: {request.POST.get('turno')}")
        print(f"Turma ID: {request.POST.get('turma')}")
        print("="*30)

        form = AlunoCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno cadastrado com sucesso.")
            return redirect('gerenciar_alunos')
        else:
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

        print("="*40)
        print("🧾 DADOS RECEBIDOS NO POST (Editar Aluno):")
        print(f"Curso ID: {curso_id}")
        print(f"Ano/Módulo: {ano_modulo}")
        print(f"Turno: {turno}")
        print(f"Turma ID: {request.POST.get('turma')}")
        print("="*40)

        form = AlunoCreateForm(request.POST, instance=aluno)

        turmas_queryset = Turma.objects.all()
        if curso_id:
            turmas_queryset = turmas_queryset.filter(curso_id=curso_id)
        if ano_modulo:
            turmas_queryset = turmas_queryset.filter(ano_modulo=ano_modulo)
        if turno:
            turmas_queryset = turmas_queryset.filter(turno=turno)

        form.fields['turma'].queryset = turmas_queryset
        form.fields['turno'].choices = [
            (valor, label) for valor, label in Turma.TURNO_CHOICES
            if valor in turmas_queryset.values_list('turno', flat=True)
        ]

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
# (Esta secção está correta e foi mantida como na última correção)

@login_required
@role_required('admin')
def gerenciar_servidores(request):
    servidores = CustomUser.objects.filter(
        tipo__in=['servidor', 'direcao']
    ).order_by('first_name', 'last_name')
    
    return render(request, 'admin/servidor_crud/gerenciar_servidores.html', {'servidores': servidores})

@login_required
@role_required('admin')
def cadastrar_servidor(request):
    if request.method == 'POST':
        form = ServidorCreateForm(request.POST)
        if form.is_valid():
            servidor = form.save(commit=False)
            tipo_escolhido = form.cleaned_data['tipo_usuario']
            servidor.tipo = tipo_escolhido 
            servidor.save() 
            messages.success(request, "Servidor cadastrado com sucesso.")
            return redirect('gerenciar_servidores')
        else:
            messages.error(request, "Erro ao cadastrar o servidor. Verifique os campos.")
    else:
        form = ServidorCreateForm()
    return render(request, 'admin/servidor_crud/cadastrar_servidor.html', {'form': form})

@login_required
@role_required('admin')
def editar_servidor(request, servidor_id):
    servidor = get_object_or_404(CustomUser, id=servidor_id, tipo__in=['servidor', 'direcao'])

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
    servidor = get_object_or_404(
        CustomUser, 
        id=servidor_id, 
        tipo__in=['servidor', 'direcao']
    )
    
    if request.method == 'POST':
        servidor.delete()
        messages.success(request, "Servidor removido com sucesso.")
        return redirect('gerenciar_servidores')
    
    return render(request, 'admin/servidor_crud/remover_servidor.html', {'servidor': servidor})


@login_required
@role_required('admin')
def ver_detalhes_servidor(request, servidor_id):
    servidor = get_object_or_404(
        CustomUser, 
        id=servidor_id, 
        tipo__in=['servidor', 'direcao']
    )
    
    context = {
        'servidor': servidor
    }
    return render(request, 'admin/servidor_crud/detalhes_servidor.html', context)

# === VIEWS DE API ===
# (Esta secção não foi alterada)

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
# (Esta secção não foi alterada)

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
# (Esta secção não foi alterada)

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
# (Esta secção não foi alterada)

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
    return render(request, 'professor/lescionação/listar_turmas_vinculadas.html', context)

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
    return render(request, 'professor/lescionação/detalhar_turma.html', context)
    
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

    return render(request, 'professor/lescionação/detalhar_turma.html', {
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


# === LÓGICA DE ESTÁGIO (PROFESSOR) ===

# 🎯 REMOVIDO: professor_listar_dossies (obsoleto)
# 🎯 REMOVIDO: professor_analisar_dossie (obsoleto)
# 🎯 REMOVIDO: professor_encaminhar_servidor (obsoleto)

@login_required
@role_required('professor')
def professor_assinar_documento(request, documento_id):
    """
    🎯 ALTERADO: Esta função agora controla a fila de aprovação
    do professor.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id)
    estagio = documento.estagio

    # Segurança: Garante que é o orientador
    if estagio.orientador != request.user:
        messages.error(request, "Você não tem permissão para assinar este documento.")
        return redirect('professor_dashboard')
    
    # Segurança: Só pode assinar se o status for o correto
    if documento.status != 'AGUARDANDO_ASSINATURA_PROF':
        messages.warning(request, "Este documento não está (ou não está mais) aguardando sua assinatura.")
        return redirect('professor_dashboard')

    # --- Executa a Ação de Assinar ---
    documento.assinado_orientador_em = now()
    
    # --- LÓGICA DA FILA (baseado no seu fluxo) ---
    tipo = documento.tipo_documento
    
    if tipo == 'TERMO_COMPROMISSO':
        # Próximo passo: Direção
        documento.status = 'AGUARDANDO_ASSINATURA_DIR'
        
    elif tipo == 'FICHA_PESSOAL' or tipo == 'AVALIACAO_ORIENTADOR':
        # Fim da fila
        documento.status = 'CONCLUIDO'
    
    # (Qualquer outro documento não deveria chegar aqui, mas por segurança)
    else:
        documento.status = 'CONCLUIDO'
        
    documento.save()
    
    messages.success(request, f"Documento '{documento.get_tipo_documento_display()}' assinado e encaminhado!")
    
    return redirect('professor_dashboard')


@login_required
@role_required('professor')
def professor_visualizar_documento(request, documento_id):
    """
    Página GENÉRICA para o Professor VISUALIZAR e ASSINAR um documento.
    (Esta função foi mantida, mas precisa de lógica de template)
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id)
    estagio = documento.estagio

    if estagio.orientador != request.user:
        messages.error(request, "Você não tem permissão para visualizar este documento.")
        return redirect('professor_dashboard')

    dados = documento.dados_formulario or {}
    for campo in ['data_inicio', 'data_fim']:
        valor = dados.get(campo)
        if isinstance(valor, str):
            try:
                dados[campo] = datetime.date.fromisoformat(valor)
            except ValueError:
                pass 
    
    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_VISUALIZAR.html'
    else:
        messages.info(request, f"A visualização para '{documento.get_tipo_documento_display()}' ainda não foi implementada.")
        return redirect('professor_dashboard')

    context = {
        'documento': documento,
        'estagio': estagio,
        'aluno': estagio.aluno,
        'dados': dados,
        'pdf_existe': documento.pdf_supervisor_assinado.storage.exists(documento.pdf_supervisor_assinado.name) if documento.pdf_supervisor_assinado else False,
        
        # 🎯 Lógica de Assinatura para o Template
        'pode_assinar_orientador': documento.status == 'AGUARDANDO_ASSINATURA_PROF',
        'documento_ja_assinado_orientador': bool(documento.assinado_orientador_em),
    }
    
    return render(request, template_name, context)

# 🎯 REMOVIDO: assinar_dossie_orientador (obsoleto)

# === PROFESSOR - NOTAS ===
# (Esta secção não foi alterada)

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
    aluno = request.user
    turmas_ids = AlunoTurma.objects.filter(aluno=aluno).values_list('turma_id', flat=True)
    materias = Materia.objects.filter(turmas__id__in=turmas_ids).distinct()

    boletim = []
    for materia in materias:
        nota = Nota.objects.filter(aluno=aluno, materia=materia).first()
        boletim.append({'materia': materia, 'nota': nota})

    return render(request, 'aluno/boletim/boletim.html', {'boletim': boletim, 'aluno': aluno})


@login_required
@role_required('aluno')
def gestao_estagio_aluno(request):
    hoje = datetime.date.today()
    
    # 🎯 CORREÇÃO: Usar o status_geral 'RASCUNHO_ALUNO' do models.py
    estagio, criado = Estagio.objects.get_or_create(
        aluno=request.user,
        defaults={
            'status_geral': 'RASCUNHO_ALUNO',
            'data_inicio': hoje,
            'data_fim': hoje,
            'supervisor_nome': '(Ainda não definido)', 
            'supervisor_empresa': '(Ainda não definido)',
            'supervisor_cargo': '(Ainda não definido)',
        }
    )

    if criado:
        tipos_de_documento = DocumentoEstagio.TIPO_DOCUMENTO_CHOICES
        documentos_para_criar = []
        for tipo_id, nome_legivel in tipos_de_documento:
            documentos_para_criar.append(
                DocumentoEstagio(
                    estagio=estagio,
                    tipo_documento=tipo_id,
                    status='RASCUNHO' # Status do Documento
                )
            )
        DocumentoEstagio.objects.bulk_create(documentos_para_criar)
        messages.info(request, "Seu Dossiê de Estágio foi criado. Por favor, preencha os documentos necessários.")

    return redirect('detalhes_estagio_aluno')


@login_required
@role_required('aluno')
def detalhes_estagio_aluno(request):
    estagio = get_object_or_404(Estagio, aluno=request.user)
    documentos_qs = DocumentoEstagio.objects.filter(estagio=estagio)
    
    ordem_desejada = [
        'TERMO_COMPROMISSO', 'FICHA_IDENTIFICACAO', 'FICHA_PESSOAL',
        'AVALIACAO_ORIENTADOR', 'AVALIACAO_SUPERVISOR', 
        'COMP_RESIDENCIA', 'COMP_AGUA_LUZ', 'ID_CARD', 
        'SUS_CARD', 'VACINA_CARD', 'APOLICE_SEGURO',
    ]
    docs_encontrados = {doc.tipo_documento: doc for doc in documentos_qs}
    
    documentos_ordenados = []
    for tipo in ordem_desejada:
        if tipo in docs_encontrados:
            documentos_ordenados.append(docs_encontrados[tipo])

    # 🎯 CORREÇÃO: Lógica de 'all_docs_concluidos' removida
    # pois o envio não é mais por dossiê.
    
    context = {
        'estagio': estagio,
        'documentos': documentos_ordenados,
    }

    return render(request, 'aluno/estagio/detalhes_estagio.html', context)


@login_required
@role_required('aluno')
def visualizar_documento_estagio(request, documento_id):
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    estagio = documento.estagio 

    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_VISUALIZAR.html'
    else:
        messages.error(request, "A visualização para este tipo de documento ainda não foi criada.")
        return redirect('detalhes_estagio_aluno')

    dados = documento.dados_formulario or {}

    for campo in ['data_inicio', 'data_fim']:
        valor = dados.get(campo)
        if isinstance(valor, str):
            try:
                dados[campo] = datetime.date.fromisoformat(valor)
            except ValueError:
                pass
    
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
        'pdf_existe': pdf_existe,
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
            documento.pdf_supervisor_assinado.delete(save=True) 
            messages.success(request, "O PDF anexado foi removido com sucesso.")
        else:
            messages.warning(request, "Nenhum PDF estava anexado a este documento.")

    return redirect('visualizar_documento_estagio', documento_id=documento.id)

@login_required
@role_required('aluno')
def assinar_documento_aluno(request, documento_id):
    """
    🎯 ALTERADO: Esta é a função "gatilho" que inicia a fila
    de aprovação para cada documento.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    
    # 🎯 CORREÇÃO: Verifica o status do DOCUMENTO, não do Dossiê
    if documento.status != 'RASCUNHO':
        messages.error(request, "Este documento não está mais em modo 'Rascunho' e não pode ser assinado.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)

    # (Verificação do Orientador para o Termo)
    if documento.tipo_documento == 'TERMO_COMPROMISSO' and not documento.estagio.orientador:
        messages.error(request, "Você precisa 'Editar' e selecionar um Professor Orientador antes de assinar o Termo de Compromisso.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)
        
    documento.assinado_aluno_em = now()
    
    # --- LÓGICA DA FILA (baseado no seu fluxo) ---
    tipo = documento.tipo_documento
    
    if tipo == 'TERMO_COMPROMISSO' or tipo == 'FICHA_PESSOAL':
        # Próximo passo: Professor
        documento.status = 'AGUARDANDO_ASSINATURA_PROF'
        
    elif tipo == 'FICHA_IDENTIFICACAO' or tipo == 'AVALIACAO_SUPERVISOR':
        # Fim da fila
        documento.status = 'CONCLUIDO'
        
    # (A Avaliação do Orientador é preenchida pelo Professor, não pelo aluno)
    # (Para todos os outros (Comprovantes, etc) que o aluno só anexa)
    else:
        documento.status = 'CONCLUIDO' 

    documento.save()
    
    messages.success(request, "Documento assinado e encaminhado para a próxima etapa!")
    
    # Quando o aluno assina o primeiro doc, o Dossiê muda de Rascunho
    if documento.estagio.status_geral == 'RASCUNHO_ALUNO':
        documento.estagio.status_geral = 'EM_ANDAMENTO'
        documento.estagio.save()
    
    return redirect('visualizar_documento_estagio', documento_id=documento.id)


# 🎯 REMOVIDO: submeter_dossie_orientador (obsoleto)


@login_required
@role_required('aluno')
def preencher_documento_estagio(request, documento_id):
    documento = get_object_or_404(DocumentoEstagio, id=documento_id, estagio__aluno=request.user)
    estagio = documento.estagio 

    # 🎯 CORREÇÃO: Aluno só pode editar se o Dossiê for rascunho
    # OU se o documento específico for rascunho
    if estagio.status_geral != 'RASCUNHO_ALUNO' and documento.status != 'RASCUNHO':
        messages.error(request, "Este documento não pode mais ser editado, pois já foi submetido.")
        return redirect('visualizar_documento_estagio', documento_id=documento.id)

    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        FormClass = TermoCompromissoForm
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_EDITAR.html'
    else:
        messages.error(request, f"O preenchimento online para '{documento.get_tipo_documento_display()}' ainda não está disponível.")
        return redirect('detalhes_estagio_aluno')

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, orientador_initial=estagio.orientador)
        
        if form.is_valid():
            dados_para_json = form.cleaned_data.copy()
            
            orientador_selecionado = dados_para_json.pop('orientador', None) 
            
            estagio.orientador = orientador_selecionado
            estagio.supervisor_nome = dados_para_json.get('supervisor_nome', estagio.supervisor_nome)
            estagio.supervisor_empresa = dados_para_json.get('concedente_nome', estagio.supervisor_empresa)
            data_inicio_str = dados_para_json.get('data_inicio')
            data_fim_str = dados_para_json.get('data_fim')
            
            try:
                if isinstance(data_inicio_str, str):
                    estagio.data_inicio = datetime.date.fromisoformat(data_inicio_str)
                elif isinstance(data_inicio_str, datetime.date):
                     estagio.data_inicio = data_inicio_str
                     
                if isinstance(data_fim_str, str):
                    estagio.data_fim = datetime.date.fromisoformat(data_fim_str)
                elif isinstance(data_fim_str, datetime.date):
                    estagio.data_fim = data_fim_str
            except ValueError:
                messages.error(request, "Formato de data inválido.")
                return render(request, template_name, {'form': form, 'documento': documento, 'aluno': request.user, 'estagio': estagio})
            
            estagio.save() 
            
            anexo_pdf = dados_para_json.pop('anexo_assinaturas', None) 
            if anexo_pdf:
                documento.pdf_supervisor_assinado = anexo_pdf
            elif anexo_pdf is False: 
                documento.pdf_supervisor_assinado = None
            
            if isinstance(dados_para_json.get('data_inicio'), datetime.date):
                dados_para_json['data_inicio'] = dados_para_json['data_inicio'].isoformat()
            if isinstance(dados_para_json.get('data_fim'), datetime.date):
                dados_para_json['data_fim'] = dados_para_json['data_fim'].isoformat()
            
            documento.dados_formulario = dados_para_json
            documento.save() 

            messages.success(request, f"'{documento.get_tipo_documento_display()}' salvo como Rascunho!")
            return redirect('visualizar_documento_estagio', documento_id=documento.id)
        else:
            messages.error(request, "Erro ao salvar. Verifique os campos preenchidos.")

    else: # (Método GET)
        initial_data = documento.dados_formulario
        if not initial_data.get('data_inicio'):
            initial_data['data_inicio'] = estagio.data_inicio
        if not initial_data.get('data_fim'):
            initial_data['data_fim'] = estagio.data_fim
            
        form = FormClass(initial=initial_data, orientador_initial=estagio.orientador)

    context = {
        'form': form,
        'documento': documento,
        'aluno': request.user, 
        'estagio': estagio 
    }
    return render(request, template_name, context)

# 🎯 REMOVIDO: direcao_analisar_dossie (obsoleto)


# ==========================================================
# === NOVAS VIEWS - SERVIDOR / DIREÇÃO (FLUXO DE ESTÁGIO)
# ==========================================================

@login_required
@role_required('direcao')
def direcao_assinar_documento(request, documento_id):
    """
    🎯 NOVA FUNÇÃO: Ação final para a Direção assinar um documento
    (principalmente o Termo de Compromisso).
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id)
    
    # Segurança: Só pode assinar se o status for o correto
    if documento.status != 'AGUARDANDO_ASSINATURA_DIR':
        messages.warning(request, "Este documento não está (ou não está mais) aguardando sua assinatura.")
        return redirect('servidor_dashboard')

    # --- Executa a Ação de Assinar ---
    documento.assinado_diretor_em = now()
    
    # --- LÓGICA DA FILA ---
    # Qualquer coisa que chega à Direção, termina aqui.
    documento.status = 'CONCLUIDO'
    documento.save()
    
    messages.success(request, f"Documento '{documento.get_tipo_documento_display()}' assinado e finalizado!")
    
    # (No futuro, podemos adicionar 'estagio.verificar_aprovacao_final()' aqui)
    
    return redirect('servidor_dashboard')

@login_required
@role_required('direcao') # 🎯 NOVA VIEW
def direcao_visualizar_documento(request, documento_id):
    """
    🎯 NOVA FUNÇÃO: Página para a Direção VISUALIZAR e ASSINAR
    um documento que está na sua fila.
    """
    documento = get_object_or_404(DocumentoEstagio, id=documento_id)
    estagio = documento.estagio
    
    # 1. Segurança: Garante que o documento está na fila da Direção
    if documento.status not in ['AGUARDANDO_ASSINATURA_DIR', 'CONCLUIDO']:
         messages.error(request, "Este documento não está (ou não está mais) aguardando sua assinatura.")
         return redirect('servidor_dashboard')

    # 2. Carrega dados do JSON (igual ao 'professor_visualizar_documento')
    dados = documento.dados_formulario or {}
    for campo in ['data_inicio', 'data_fim']:
        valor = dados.get(campo)
        if isinstance(valor, str):
            try:
                dados[campo] = datetime.date.fromisoformat(valor)
            except ValueError:
                pass 
    
    # 3. Define qual template HTML deve ser usado
    # (Reutiliza o template do aluno/professor)
    if documento.tipo_documento == 'TERMO_COMPROMISSO':
        template_name = 'aluno/estagio/docs/TERMO-DE-COMPROMISSO_VISUALIZAR.html'
    # (Adicionar 'elif' para outros documentos no futuro)
    else:
        messages.info(request, f"A visualização para '{documento.get_tipo_documento_display()}' ainda não foi implementada.")
        return redirect('servidor_dashboard')

    # 4. Prepara o contexto
    context = {
        'documento': documento,
        'estagio': estagio,
        'aluno': estagio.aluno,
        'dados': dados,
        'pdf_existe': documento.pdf_supervisor_assinado.storage.exists(documento.pdf_supervisor_assinado.name) if documento.pdf_supervisor_assinado else False,
        
        # 🎯 Flag para o template mostrar o botão "Assinar"
        'pode_assinar_direcao': documento.status == 'AGUARDANDO_ASSINATURA_DIR',
        'documento_ja_assinado_direcao': bool(documento.assinado_diretor_em),
    }
    
    return render(request, template_name, context)


@login_required
@role_required('servidor')
def servidor_monitorar_alunos(request):
    """
    🎯 NOVA FUNÇÃO: Página para o Servidor Admin listar todos os alunos
    do seu eixo e ver um resumo do status.
    """
    eixo_servidor = request.user.eixo
    if not eixo_servidor:
        messages.error(request, "Seu usuário não está associado a um Eixo.")
        return redirect('servidor_dashboard')

    # 1. Busca todos os alunos do eixo
    alunos_no_eixo = CustomUser.objects.filter(
        tipo='aluno',
        alunoturma_set__turma__curso__eixo=eixo_servidor
    ).distinct().order_by('first_name', 'last_name')

    # 2. Busca os dados de estágio (se existirem) para esses alunos
    estagios_map = {
        estagio.aluno_id: estagio
        for estagio in Estagio.objects.filter(
            aluno__in=alunos_no_eixo
        ).annotate(
            # Conta quantos documentos NÃO estão 'CONCLUIDO' ou 'RASCUNHO'
            docs_pendentes_count=Count('documentos', filter=~Q(documentos__status__in=['CONCLUIDO', 'RASCUNHO']))
        )
    }

    # 3. Combina os dados para o template
    alunos_data = []
    for aluno in alunos_no_eixo:
        estagio_data = estagios_map.get(aluno.id)
        alunos_data.append({
            'aluno': aluno,
            'estagio_iniciado': bool(estagio_data),
            'docs_pendentes_count': estagio_data.docs_pendentes_count if estagio_data else 0,
            'estagio_status': estagio_data.get_status_geral_display() if estagio_data else "Não Iniciado",
            'estagio_id': estagio_data.id if estagio_data else None,
        })

    context = {
        'alunos_data': alunos_data,
        'eixo_servidor': request.user.get_eixo_display
    }
    return render(request, 'servidor/administrativo/monitorar_alunos.html', context)


@login_required
@role_required('servidor')
def servidor_ver_documentos_aluno(request, aluno_id):
    """
    🎯 NOVA FUNÇÃO: Página (Checklist) para o Servidor Admin ver TODOS
    os documentos de um aluno específico.
    """
    eixo_servidor = request.user.eixo
    aluno = get_object_or_404(CustomUser, id=aluno_id, tipo='aluno')

    # 1. Busca o estágio (dossiê) do aluno
    try:
        estagio = Estagio.objects.get(aluno=aluno)
    except Estagio.DoesNotExist:
        messages.error(request, "Este aluno ainda não iniciou seu dossiê de estágio.")
        return redirect('servidor_monitorar_alunos')

    # 2. 🚨 Verificação de Segurança
    # Garante que o servidor só veja alunos do seu próprio eixo.
    aluno_pertence_ao_eixo = aluno.alunoturma_set.filter(
        turma__curso__eixo=eixo_servidor
    ).exists()
    
    if not aluno_pertence_ao_eixo:
        messages.error(request, "Você não tem permissão para ver este aluno.")
        return redirect('servidor_monitorar_alunos')

    # 3. Busca e ordena todos os documentos (lógica que já usámos)
    documentos_qs = estagio.documentos.all()
    ordem_desejada = [
        'TERMO_COMPROMISSO', 'FICHA_IDENTIFICACAO', 'FICHA_PESSOAL',
        'AVALIACAO_ORIENTADOR', 'AVALIACAO_SUPERVISOR', 
        'COMP_RESIDENCIA', 'COMP_AGUA_LUZ', 'ID_CARD', 
        'SUS_CARD', 'VACINA_CARD', 'APOLICE_SEGURO',
    ]
    docs_encontrados = {doc.tipo_documento: doc for doc in documentos_qs}
    documentos_ordenados = []
    for tipo in ordem_desejada:
        if tipo in docs_encontrados:
            documentos_ordenados.append(docs_encontrados[tipo])

    context = {
        'aluno': aluno,
        'estagio': estagio,
        'documentos': documentos_ordenados
    }
    return render(request, 'servidor/administrativo/ver_documentos_aluno.html', context)