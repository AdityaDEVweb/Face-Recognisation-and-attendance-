import unittest

from app.face.recognizer import best_match


class FaceMatchingTests(unittest.TestCase):
    def test_best_match_uses_highest_cosine_similarity(self) -> None:
        known_faces = [
            {"id": 1, "name": "Alex", "embedding": [1.0, 0.0]},
            {"id": 2, "name": "Sam", "embedding": [0.0, 1.0]},
        ]

        person, score = best_match([0.1, 0.9], known_faces)

        self.assertEqual(person["id"], 2)
        self.assertAlmostEqual(score, 0.9)

    def test_best_match_ignores_incompatible_embedding_dimensions(self) -> None:
        person, score = best_match(
            [1.0, 0.0],
            [{"id": 1, "name": "Bad vector", "embedding": [1.0]}],
        )

        self.assertIsNone(person)
        self.assertIsNone(score)


if __name__ == "__main__":
    unittest.main()