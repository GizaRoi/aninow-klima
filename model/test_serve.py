"""The local form: what it sends to the model and what it shows."""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("serve", os.path.join(HERE, "serve.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

PLACE = next(iter(S.PLACES))


def q(**kw):
    """A submitted form, parse_qs-shaped."""
    base = dict(place=PLACE, harvest="2026-11-15", next_planting="2027-05-31",
                drainage="well_drained", water="rain", priority="balanced")
    base.update(kw)
    return {k: [v] for k, v in base.items()}


def option(args, name):
    return args[args.index(name) + 1] if name in args else None


class FormToModel(unittest.TestCase):
    def test_a_place_name_becomes_coordinates(self):
        args = S.to_args(q())
        self.assertEqual(float(option(args, "--lat")), 15.72)
        self.assertEqual(float(option(args, "--lon")), 120.90)
        self.assertEqual(option(args, "--province"), "Nueva Ecija")

    def test_an_unknown_place_is_refused(self):
        with self.assertRaises(ValueError):
            S.to_args(q(place="Somewhere Else, Nowhere"))

    def test_soil_values_are_ignored_while_the_switch_is_off(self):
        args = S.to_args(q(soil_ph="4.8", soil_texture="heavy"))
        self.assertNotIn("--soil-ph", args)
        self.assertNotIn("--soil-texture", args)

    def test_soil_values_are_used_when_the_switch_is_on(self):
        args = S.to_args(q(soil_test="1", soil_ph="4.8", soil_texture="heavy"))
        self.assertEqual(float(option(args, "--soil-ph")), 4.8)
        self.assertEqual(option(args, "--soil-texture"), "heavy")

    def test_pass_mark_is_only_sent_from_the_advanced_view(self):
        self.assertNotIn("--pass-mark", S.to_args(q(pass_mark="0.9")))
        args = S.to_args(q(advanced="1", pass_mark="0.7"))
        self.assertEqual(float(option(args, "--pass-mark")), 0.7)

    def test_land_preparation_days_are_sent_from_the_advanced_view(self):
        self.assertNotIn("--turnaround-days", S.to_args(q(turnaround="20")))
        args = S.to_args(q(advanced="1", turnaround="20"))
        self.assertEqual(option(args, "--turnaround-days"), "20")
        with self.assertRaises(ValueError):
            S.to_args(q(advanced="1", turnaround="2.5"))

    def test_the_main_crop_is_sent_and_must_be_known(self):
        self.assertEqual(option(S.to_args(q()), "--main-crop"), "rice")
        self.assertEqual(option(S.to_args(q(main_crop="tomato")), "--main-crop"), "tomato")
        with self.assertRaises(ValueError):
            S.to_args(q(main_crop="durian"))

    def test_a_resting_field_is_a_valid_answer(self):
        self.assertEqual(option(S.to_args(q(main_crop="fallow")), "--main-crop"), "fallow")
        page = S.page_html(q(main_crop="fallow"))
        self.assertIn("Nothing: the field is resting", page)
        self.assertNotIn("your crop now", page)
        self.assertNotIn("class=\"err\"", page)

    def test_the_whole_plan_is_only_sent_when_its_switch_is_on(self):
        args = S.to_args(q(prep="30", picking="14"))
        self.assertNotIn("--prep-days", args)
        args = S.to_args(q(plan="1", prep="30", picking="14"))
        self.assertEqual(option(args, "--prep-days"), "30")
        self.assertEqual(option(args, "--picking-days"), "14")
        with self.assertRaises(ValueError):
            S.to_args(q(plan="1", prep="-3"))

    def test_the_plan_is_shown_in_days_and_can_rule_a_crop_out(self):
        page = S.page_html(q(plan="1", prep="30", picking="20", advanced="1", turnaround="10"))
        self.assertIn("30 days before planting, 50 growing, 20 picking, 10 clearing "
                      "= 110 of your 197 days, 87 to spare", page)
        self.assertIn("planted\n    30 days after harvest", page)
        out = page.split("Not recommended here")[1]
        self.assertIn("Your whole plan for it", out)        # onion: 30+150+20+10 > 197

    def test_cautions_are_shown_and_never_hidden(self):
        page = S.page_html(q())
        self.assertIn("Only partly checked: its source gives no soil texture", page)
        self.assertIn("the DA crop guide recommends 21 to 24", page)      # tomato
        self.assertIn("Same plant family as Palay", page)                  # maize

    def test_no_suitable_recommendation_is_said_in_words(self):
        page = S.page_html(q(place="Batac, Ilocos Norte"))
        self.assertIn("No suitable recommendation", page)
        self.assertIn("It is not advice to plant the first", page)
        self.assertNotIn("Suitable here in a typical year", page)
        pilot = S.page_html(q())
        self.assertNotIn("No suitable recommendation", pilot)
        self.assertIn("Suitable here in a typical year:</strong> Labanos, Munggo.", pilot)

    def test_every_place_on_the_list_has_weather_and_soil(self):
        self.assertGreaterEqual(len(S.PLACES), 7)
        for name in S.PLACES:
            page = S.page_html(q(place=name))
            self.assertIn("Crop options", page, f"{name} could not be scored")
            self.assertNotIn('class="err"', page)

    def test_planting_before_harvest_is_refused(self):
        with self.assertRaises(ValueError):
            S.to_args(q(harvest="2027-05-31", next_planting="2026-11-15"))

    def test_a_soil_ph_outside_the_possible_range_is_refused(self):
        with self.assertRaises(ValueError):
            S.to_args(q(soil_test="1", soil_ph="14"))


class Page(unittest.TestCase):
    """Runs the real model once per case; slow."""

    def test_the_form_never_asks_for_coordinates(self):
        page = S.page_html({})
        self.assertNotIn("Latitude", page)
        self.assertNotIn("Longitude", page)
        self.assertIn("Where is your field?", page)

    def test_the_farmer_view_leaves_the_detail_out(self):
        page = S.page_html(q())
        self.assertIn("Munggo", page)
        self.assertIn("22 of 41", page)
        self.assertNotIn("El Ni&ntilde;o 5 of 12", page)
        self.assertIn("References", page)
        for jargon in ("Kc", "EcoCrop climate envelope", "Wilson", "Method notes",
                       "15.72"):
            self.assertNotIn(jargon, page.split("<footer>")[0].split("</form>")[1],
                             f"{jargon!r} leaked into the farmer view")

    def test_the_advanced_view_carries_the_detail(self):
        page = S.page_html(q(advanced="1"))
        for detail in ("Weakest condition", "Wilson", "El Ni&ntilde;o years", "Planting dates", "Method notes",
                       "15.72", "FAO-56 T12"):
            self.assertIn(detail, page)

    def test_water_is_given_as_a_depth_and_against_rice(self):
        self.assertEqual(S.water_plain(44.4, 50, 531.0),
                         ("About 4 cm", "of water over the whole field, spread across "
                                        "50 days. Rice needs about 12 times more."))
        self.assertEqual(S.water_plain(531.0, 80, 531.0, is_rice=True)[0], "About 53 cm")
        self.assertEqual(S.water_plain(0.0, 50)[0], "None")
        self.assertEqual(S.water_plain(None, 50)[0], "Not worked out")
        page = S.page_html(q())
        self.assertIn("About 4 cm", page)
        self.assertNotIn("44 mm", page.split("<footer>")[0].split("</form>")[1])

    def test_another_main_crop_is_the_one_compared_against(self):
        page = S.page_html(q(main_crop="tomato"))
        self.assertIn("your crop now",
                      page.split("</form>")[1].split("Kamatis <small>")[1].split("</span>")[0])
        self.assertIn("Kamatis needs about", page)
        self.assertNotIn("Palay needs about", page)

    def test_names_and_small_wording(self):
        page = S.page_html(q())
        self.assertIn("Sitaw <small>Yardlong bean", page)
        self.assertIn("Habichuelas <small>Snap bean", page)
        self.assertIn("3.4 km away", page)
        batac = S.page_html(q(place="Batac, Ilocos Norte"))
        self.assertIn("from a soil sample tested at this place", batac)
        self.assertNotIn("0.0 km", batac)
        self.assertNotIn("soil ph.", S.page_html(q(place="Maramag, Bukidnon", water="irrigation")))

    def test_a_guide_crop_outside_its_range_says_why(self):
        page = S.page_html(q())
        out = page.split("Not recommended here")[1]
        self.assertIn("Repolyo", out)
        self.assertIn("Too warm here. The DA crop guide recommends 15 to 20", out)

    def test_a_field_that_holds_water_leaves_only_rice(self):
        page = S.page_html(q(drainage="poorly_drained"))
        self.assertIn("Not recommended here", page)
        rated = page.split("Not recommended here")[0]
        self.assertIn("Palay", rated)
        for name in ("Munggo", "Talong", "Kamatis", "Kalabasa", "Sitaw"):
            self.assertNotIn(name, rated.split("</form>")[1])
        self.assertIn("you said water stays on your field", page)

    def test_the_rating_follows_the_weakest_condition(self):
        # rainfed: rain covers ~1/6 of rice's need
        page = S.page_html(q())
        rice = page.split("</form>")[1].split("Palay <small>")[1].split("</div>")[0]
        self.assertIn("Poor fit", rice)


if __name__ == "__main__":
    unittest.main()
