### Example files that demonstrate typical conversions with voc4cat

For a new vocabulary one would probably start with an xlsx file that does not yet have IRIs.
In this case hierarchies can be expressed best by indentation:

- `photocatalysis_example_indented_prelim-IDs.xlsx`
  - This file uses Excel/xlsx-indentation to express hierarchy. It does contain temporary IRIs for concepts. At least some preliminary IRIs are required to convert the hierarchy from indentation to children-IRI form. You may also use text-based IRIs as preliminary IRIs.
- `photocatalysis_example_prelim-IDs.xlsx`
  - This results from processing the previous file with voc4cat using the `--from-indent` option.
- `photocatalysis_example.xlsx`
  - This results from processing the previous file with voc4cat using the `--make-ids temp 1` option which replaces the temporary "temp:###"-IRIs with IRIs containing numeric IDs starting from 1. The prefix is replaced by the concept scheme IRI from the "concept scheme" sheet and the standard 7-digit IDs are used instead of the 3 digits of the preliminary IRIs.
  - If this file is further processed with voc4cat without options, the SKOS file `photocatalysis_example.ttl` is generated.
  - Running voc4cat on the turtle file generates again the xlsx file. - The conversion works both ways!
