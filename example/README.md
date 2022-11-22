Example files showing what voc4cat can do:

- `Photocatalysis_LIKAT_template043_orig-fixed.xlsx`
  - A draft of a potocatalysis vocabulary: This has still the original structure and contents; only spelling and link errors were fixed. The hierarchy was created by the now removed `-r` / `--add-related` option from the extra column on the right in sheets Concepts & Collections. These columns are not part of the standard template.
- `Photocatalysis_LIKAT_template043_final.xlsx`
  - Same contents as the first file but the extra column in the sheets Concepts & Collections was removed.
- `Photocatalysis_LIKAT_template043_final.ttl`
  - Results of processing the previous file with voc4cat without options (which does convert to turtle).

The above example is not representing the most typical workflow. In practise one would start creating vocabularies from a file that does not yet have IRIs and therefore has to express hierarchies by indent:

- `Photocatalysis_LIKAT_template043_indent.xlsx` (WIP)
  - Same content as first file, but it uses Excel indentation to express hierarchy and does not contain IRIs for concepts.
- `Photocatalysis_LIKAT_template043_indent_iri.xlsx` (WIP)
  - Results of processing the previous file with voc4cat using the `-i` option.
- `Photocatalysis_LIKAT_template043_indent_final.xlsx` (WIP)
  - Result of processing the previous file with voc4cat using the `--hierarchy-from-indent` option. If this file is converted to turtle
  - If this file is futher processed with voc4cat without options, the resulting turtle should be identical to the turtle file from above (`Photocatalysis_LIKAT_template043_final.ttl`)

Files demonstrating the different ways how to express concept-hierarchies:

- Children URIs: concept_hierarchy_043_4Cat.xlsx
- Excel indentation: indent_043_4Cat.xlsx
- Three spaces for indentation: indent_3spaces_043_4Cat.xlsx
