from django.core.management.base import BaseCommand
from analyzer.models import BloodParameter

class Command(BaseCommand):
    help = "Load blood parameters"

    def handle(self, *args, **kwargs):
        data = [
            ("Hemoglobin", "CBC", "Hb,HGB", "g/dL",13.0, 17.0),
            ("RBC", "CBC", "RBC,RBC Count", "million/uL", 4.5, 5.9),
            ("WBC", "CBC", "WBC,TLC", "cells/uL",4000, 11000),
            ("Platelets", "CBC", "PLT,Platelet Count", "cells/uL",150000, 450000),
            ("Hematocrit", "CBC", "HCT,PCV", "%",40, 50),
            ("MCV", "CBC", "MCV", "fL",80, 100),
            ("MCH", "CBC", "MCH", "pg",27, 33),
            ("MCHC", "CBC", "MCHC", "g/dL",32, 36),
            ("RDW", "CBC", "RDW", "%",11.5, 14.5),
            ("Neutrophils", "DIFF", "Neut,Neutrophils", "%", 40, 70),
            ("Lymphocytes", "DIFF", "Lymph,Lymphocytes", "%", 20, 40),
            ("Monocytes", "DIFF", "Mono,Monocytes", "%", 2, 8),
            ("Eosinophils", "DIFF", "Eos,Eosinophils", "%", 1, 4),
            ("Basophils", "DIFF", "Baso,Basophils", "%", 0.5, 1),
        ]

        for p in data:
            BloodParameter.objects.get_or_create(
                name=p[0],
                category=p[1],
                common_names=p[2],
                unit=p[3],
                normal_min=p[4],
                normal_max=p[5],
            )

        self.stdout.write("Blood parameters loaded successfully.")
