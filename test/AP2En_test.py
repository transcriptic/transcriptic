import pytest
import unittest
import json
from transcriptic import english


class AP2EnTestCase(unittest.TestCase):
    def test_web_example(self):

        with open("./test/resources/web_example.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            forest, [[1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11]]
        )

    def test_med_json_job_tree(self):

        pjsonString = """{
              "refs": {
                "3-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "5-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "4-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "1-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "0-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "6-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                },
                "2-384-pcr": {
                  "new": "384-pcr",
                  "discard": true
                }
              },
              "instructions": [
                {
                  "groups": [
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "3-384-pcr/383",
                          "from": "3-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "3-384-pcr/382",
                          "from": "3-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "5-384-pcr/383",
                          "from": "5-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "5-384-pcr/382",
                          "from": "5-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "4-384-pcr/383",
                          "from": "4-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "4-384-pcr/382",
                          "from": "4-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "1-384-pcr/383",
                          "from": "1-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "1-384-pcr/382",
                          "from": "1-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "0-384-pcr/383",
                          "from": "0-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "0-384-pcr/382",
                          "from": "0-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "6-384-pcr/383",
                          "from": "6-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "6-384-pcr/382",
                          "from": "6-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "2-384-pcr/383",
                          "from": "2-384-pcr/0"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    },
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter",
                          "to": "2-384-pcr/382",
                          "from": "2-384-pcr/1"
                        }
                      ],
                      "x_tip_type": "filtered50"
                    }
                  ],
                  "op": "pipette"
                }
              ]
            }
            """
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            forest,
            [[1, [2]], [3, [4]], [5, [6]], [7, [8]], [9, [10]], [11, [12]], [13, [14]]],
        )

    def test_measure_suite(self):
        """
        Desired Output:
        1. Measure concentration of 2.0 microliters DNA source aliquots
        2. Measure mass of test_plate2
        3. Measure volume of 12 wells from test_plate
        4. Measure volume of 8 wells from test_plate2
        """

        with open("./test/resources/measure_suite.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Measure concentration of 2.0 microliters DNA source aliquots of test_plate2",
                "Measure mass of test_plate2",
                "Measure volume of 12 wells from test_plate",
                "Measure volume of 8 wells from test_plate2",
            ],
        )
        self.assertEqual(forest, [[1, [2, [4]]], [3]])

    def test_mag_incubate(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically incubate pcr_0 for 30.0 minutes with a tip position of 1.5
        """

        with open("./test/resources/mag_incubate.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                "Distribute from test/1 into wells test/7, test/8, test/9",
                "Distribute from test/2 into wells test/10",
                "Distribute from test/0 into wells test/1",
                "Magnetically incubate pcr_0 for 30.0 minutes with a tip position of 1.5",
            ],
        )
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_mix(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically mix pcr_0 beads for 30.0 seconds at an amplitude of 0
        """

        with open("./test/resources/mag_mix.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                "Distribute from test/1 into wells test/7, test/8, test/9",
                "Distribute from test/2 into wells test/10",
                "Distribute from test/0 into wells test/1",
                "Magnetically mix pcr_0 beads for 30.0 seconds at an amplitude of 0",
            ],
        )
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_dry(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically dry pcr_0 for 30.0 minutes
        """

        with open("./test/resources/mag_dry.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                "Distribute from test/1 into wells test/7, test/8, test/9",
                "Distribute from test/2 into wells test/10",
                "Distribute from test/0 into wells test/1",
                "Magnetically dry pcr_0 for 30.0 minutes",
            ],
        )
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_collect(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically collect pcr_0 beads for 5 cycles with a pause duration of 30.0 seconds
        """

        with open("./test/resources/mag_collect.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                "Distribute from test/1 into wells test/7, test/8, test/9",
                "Distribute from test/2 into wells test/10",
                "Distribute from test/0 into wells test/1",
                "Magnetically collect pcr_0 beads for 5 cycles with a pause duration of 30.0 seconds",
            ],
        )
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_purify(self):
        """
        Desired Output:
        1. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        2. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        3. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        """

        with open("./test/resources/purify.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Perform gel purification on the 0.8% agarose gel with band range(s) 0-10",
                "Perform gel purification on the 0.8% agarose gel with band range(s) 0-10",
                "Perform gel purification on the 0.8% agarose gel with band range(s) 0-10",
            ],
        )
        self.assertEqual(forest, [[1, [2, [3]]]])

    def test_dispense_suite(self):
        """
        Desired Output:
        1. Dispense 100 microliters of water to the full plate of sample_plate5
        2. Dispense corresponding amounts of water to 12 column(s) of sample_plate5
        3. Dispense 50 microliters of reagent with resource ID rs17gmh5wafm5p to the full plate of sample_plate5
        """

        with open("./test/resources/dispense.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Dispense 100 microliters of water to the full plate of sample_plate5",
                "Dispense corresponding amounts of water to 12 column(s) of sample_plate5",
                "Dispense 50 microliters of resource with resource ID rs17gmh5wafm5p to the full plate of sample_plate5",
            ],
        )
        self.assertEqual(forest, [[1, [2, [3]]]])

    def test_illumina(self):
        """
        Desired Output:
        1. Illumina sequence wells test_plate6/0, test_plate6/1 with library size 34
        """

        with open("./test/resources/illumina.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Illumina sequence wells test_plate6/0, test_plate6/1 with library size 34"
            ],
        )
        self.assertEqual(forest, [[1]])

    def test_flow(self):
        """
        Desired Output:
        1. Perform flow cytometry on well0 with the respective FSC and SSC channel parameters
        """

        with open("./test/resources/flow.json") as data_file:
            pjson = json.load(data_file)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output,
            [
                "Perform flow cytometry on test_plate/0 with the respective FSC and SSC channel parameters"
            ],
        )
        self.assertEqual(forest, [[1]])
