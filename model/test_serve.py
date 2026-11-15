"""Tests for the local form: what it sends to the model and what it shows.

    python -m unittest discover model -v
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("serve", os.path.join(HERE, "serve.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

PLACE = next(iter(S.PLACES))


def q(**kw):
    """A submitted form, in the shape urllib.parse.parse_qs gives."""
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

    def test_planting_before_harvest_is_refused(self):
        with self.assertRaises(ValueError):
            S.to_args(q(harvest="2027-05-31", next_planting="2026-11-15"))

    def test_a_soil_ph_outside_the_possible_range_is_refused(self):
        with self.assertRaises(ValueError):
            S.to_args(q(soil_test="1", soil_ph="14"))


class Page(unittest.TestCase):
    """These run the real model, once per case, so they take a few seconds."""

    def test_the_form_never_asks_for_coordinates(self):
        page = S.page_html({})
        self.assertNotIn("Latitude", page)
        self.assertNotIn("Longitude", page)
        self.assertIn("Where is your field?", page)

    def test_the_farmer_view_leaves_the_detail_out(self):
        page = S.page_html(q())
        self.assertIn("Munggo", page)
        self.assertIn("38 of 41", page)
        self.assertIn("References", page)
        for jargon in ("Kc", "EcoCrop climate envelope", "Wilson", "Method notes",
                       "15.72"):
            self.assertNotIn(jargon, page.split("<footer>")[0].split("</form>")[1],
                             f"{jargon!r} leaked into the farmer view")

    def test_the_advanced_view_carries_the_detail(self):
        page = S.page_html(q(advanced="1"))
        for detail in ("Overall score", "Wilson", "Planting dates", "Method notes",
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

    def test_a_field_that_holds_water_leaves_only_rice(self):
        page = S.page_html(q(drainage="poorly_drained"))
        self.assertEqual(page.count("Not suited"), 3)
        self.assertIn("you said water stays on your field", page)

    def test_the_rating_follows_the_weakest_condition(self):
        # Rain covers about a sixth of rice's need on a rainfed field, so rice
        # must not be shown as a good or fair fit whatever the combined score is.
        page = S.page_html(q())
        rice = page.split("Palay")[1].split("</div>")[0]
        self.assertIn("Poor fit", rice)


if __name__ == "__main__":
    unittest.main()
