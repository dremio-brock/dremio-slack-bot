from slack.web.client import WebClient
from slack.web.classes import dialogs
from flask import Flask, json, request, make_response
import env
import os
import matplotlib
import matplotlib.pyplot as plt
from dremio_client import init


app = Flask(__name__)  # create the Flask app

def setup_app(app):
    # prevent matlab from opening a windows
    matplotlib.use('agg')

    # Dremio connection
    dremio_client = init()

    # Slack part
    client = WebClient(token=os.environ['SLACK_API_TOKEN'])

    # Method to call the dialog
    @app.route('/slack/nyc_request', methods=['POST'])
    def nyc_report():
        # options for when the report runs.
        report_grain = [
            {
                "label": "Week",
                "value": "WEEK"
            },
            {
                "label": "Month",
                "value": "MONTH"
            },
            {
                "label": "Quarter",
                "value": "QUARTER"
            },
            {
                "label": "Year",
                "value": "YEAR"
            }
        ]

        builder = (
            dialogs.DialogBuilder()
                .title("NYC Taxi Report")
                .callback_id("NycTaxiReport")
                .static_selector(name="report",
                                 label="Select a report", options=report_grain)
        )

        trigger_id = request.form.get('trigger_id')
        client.dialog_open(dialog=builder.to_dict(), trigger_id=trigger_id)

        return make_response("", 200)

    # Method that receives the form post, runs the query on Dremio and posts the resulting image to the slack channel
    @app.route('/slack', methods=['POST'])
    def return_report():
        report_gain = json.loads(request.form['payload'])['submission']['report']
        channel = json.loads(request.form['payload'])['channel']['id']
        report = get_report(report_gain)
        client.files_upload(
            channels=channel,
            file=report,
            filename='report.png',
            title='report'
        )
        return make_response("", 200)

    # Function to send sql to dremio, plot the results and save the image
    def get_report(report_request):
        query = 'SELECT \
          {}("trips"."pickup_datetime") AS "pickup_date",\
          SUM(1) AS "# of pickups"\
        FROM "NYC Taxi"."trips" "trips"\
        GROUP BY 1 order by 1'
        df = dremio_client.query(query.format(report_request))
        df.plot(x='pickup_date', y='# of pickups')
        plt.savefig('result.png')

        return os.getcwd() + '/result.png'


setup_app(app)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)  # run app in debug mode on port 8000