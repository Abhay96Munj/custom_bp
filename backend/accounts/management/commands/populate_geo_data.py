import os
import json
from django.core.management.base import BaseCommand
from accounts.models import Country, State


class Command(BaseCommand):
    help = "Populate country and state data from an external source"

    def handle(self, *args, **kwargs):
        # # Example API: Restcountries
        # url = os.getenv("GEO_DATA_FETCH_URL")
        # response = requests.get(url)
        # countries_data = response.json()
        countries_data = json.loads(
            open(
                os.path.join(os.path.dirname(__file__), "countries+states.json")
            ).read()
        )
        if Country.objects.count() > 0 and State.objects.count() > 0:
            self.stdout.write(
                self.style.WARNING(
                    "Country and state data already exists. Skipping population."
                )
            )
            return
        for country_data in countries_data:
            country, created = Country.objects.get_or_create(
                name=country_data["name"], code=country_data["iso3"]
            )
            print(f"Country: {country.name}, Created: {created}")
            for data in country_data.get("states", []):
                State.objects.get_or_create(name=data["name"], country=country)
                print(f"State: {data["name"]}")

        self.stdout.write(
            self.style.SUCCESS("Successfully populated country and state data")
        )
