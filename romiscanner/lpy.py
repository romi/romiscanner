from romidata.task import FilesetExists

import luigi


class LpyFileset(FilesetExists):
    scan_id = luigi.Parameter()
    fileset_id = "lpy"
