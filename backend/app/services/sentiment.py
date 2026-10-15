from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_review_text(text: str) -> float:
    if not text:
        return 0.0
    return _analyzer.polarity_scores(text)["compound"]


def average_sentiment(review_texts: list[str]) -> float:
    if not review_texts:
        return 0.0
    scores = [score_review_text(t) for t in review_texts if t]
    return sum(scores) / len(scores) if scores else 0.0
