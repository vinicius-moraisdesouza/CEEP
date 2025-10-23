from django.core.management.base import BaseCommand
from core.models import Materia

class Command(BaseCommand):
    help = "Popula o banco de dados com as matérias básicas e técnicas do CEEP"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🚀 Iniciando o seed de matérias..."))

        # Matérias da base comum
        materias_base = [
            "Português", "Matemática", "Química", "Biologia", 
            "Física", "Geografia", "História",
        ]

        # Matérias da base técnica (usando os nomes dos cursos)
        materias_tecnicas = [
            "ADMINISTRAÇÃO", "ANÁLISES CLÍNICAS", "BIOTECNOLOGIA", 
            "FINANÇAS", "LOGÍSTICA", "SEGURANÇA DO TRABALHO", 
            "SERVIÇOS JURÍDICOS", "EDIFICAÇÕES", "ENFERMAGEM", "PANIFICAÇÃO",
        ]
        
        # Juntamos as duas listas
        todas_as_materias = materias_base + materias_tecnicas
        
        materias_criadas = 0
        materias_existentes = 0

        for nome_materia in todas_as_materias:
            # Usamos get_or_create para evitar duplicatas.
            # Ele procura uma matéria com aquele nome. Se não achar, cria uma nova.
            obj, criado = Materia.objects.get_or_create(nome=nome_materia)

            if criado:
                materias_criadas += 1
                self.stdout.write(f"   - Matéria '{obj.nome}' criada.")
            else:
                materias_existentes += 1
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Seed finalizado!"))
        self.stdout.write(f"   - Novas matérias criadas: {materias_criadas}")
        self.stdout.write(f"   - Matérias que já existiam: {materias_existentes}")