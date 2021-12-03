from parse_wkbk import Parser
from data_reader import dataReader
from display_data import displayData
from lab_ppt import powerPoint
from configs import Config
from analyze import Analyzer

if __name__ == '__main__':
    configs = Config('config.ini')
    file_list = configs.file_list
    pickled_data = configs.pickled_data
    decomposed_data = configs.decomposed_data
    headings = configs.headings

    #define parameter of interest
    parameter = 'bdi sum'

    #graphing
    data = pd.read_pickle(pickled_data)
    graph = displayData(data)
    graph.output_full_stack(graph.decomposed_data, parameter)

    #analysis
    analyzer = Analyzer()
    ranked_df = analyzer.rank_r2_values()

    #make ppt and shuffle files around
    cwd = os.getcwd()
    d = datetime.datetime.today().strftime('%Y-%m-%d')
    presentation = powerPoint()
    presentation.make_title()
    presentation.get_images()  # Moves the "gotten" images to the folder as it loads
    # them into the pptx.
    name = f"{parameter} summary.pptx"
    presentation.prs.save(name)
    shutil.move(name, cwd + "\\" + parameter + "\\")
    try:
        shutil.move('ranked_r2.xlsx',cwd + "\\" + d + "\\" )


